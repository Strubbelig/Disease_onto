import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const repoRoot = path.resolve("../..");
const tableDir = path.join(repoRoot, "Extraction Tables");
const inputCsv = path.join(tableDir, "native_class_citation_coverage.csv");
const suggestionJson = path.join(repoRoot, ".codex_tmp", "citation_workbook", "citation_suggestion_lookup.json");
const outputXlsx = path.join(tableDir, "Ontologies_Needing_Citations.xlsx");

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];
    if (char === '"' && inQuotes && next === '"') {
      cell += '"';
      i += 1;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      row.push(cell);
      cell = "";
    } else if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") i += 1;
      row.push(cell);
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }
  if (cell || row.length) {
    row.push(cell);
    if (row.some((value) => value !== "")) rows.push(row);
  }
  const [headers, ...dataRows] = rows;
  return dataRows.map((values) =>
    Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""])),
  );
}

function uniqueSorted(values) {
  return [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b));
}

function matrixFromObjects(rows, columns) {
  return [columns.map((column) => column.header)].concat(
    rows.map((row) => columns.map((column) => row[column.key] ?? "")),
  );
}

function writeMatrix(sheet, matrix) {
  if (!matrix.length) return;
  sheet.getRangeByIndexes(0, 0, matrix.length, matrix[0].length).values = matrix;
}

function formatSheet(sheet, rowCount, colCount, title) {
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  const used = sheet.getRangeByIndexes(0, 0, Math.max(rowCount, 1), colCount);
  used.format.font.name = "Aptos";
  used.format.font.size = 10;
  used.format.wrapText = true;
  const header = sheet.getRangeByIndexes(0, 0, 1, colCount);
  header.format.fill.color = "#1F4E78";
  header.format.font.color = "#FFFFFF";
  header.format.font.bold = true;
  header.format.verticalAlignment = "center";
  header.format.rowHeightPx = 34;
  used.format.borders = { preset: "outside", style: "thin", color: "#A6A6A6" };
  if (rowCount > 1) {
    sheet.getRangeByIndexes(1, 0, rowCount - 1, colCount).format.borders = {
      preset: "inside",
      style: "thin",
      color: "#E7EAF0",
    };
  }
  used.format.autofitColumns();
  used.format.autofitRows();
  const widths = {
    "Ontologies needing citation": [120, 95, 150, 220, 320, 120, 120, 120, 150, 260, 180, 220],
    "Class rows": [120, 95, 150, 360, 150, 320, 120, 120, 220],
    Summary: [280, 120],
  }[title] ?? [];
  widths.forEach((width, index) => {
    sheet.getRangeByIndexes(0, index, rowCount, 1).format.columnWidthPx = width;
  });
}

const csvText = await fs.readFile(inputCsv, "utf8");
const suggestionPayload = JSON.parse(await fs.readFile(suggestionJson, "utf8"));
const suggestions = suggestionPayload.rows ?? {};
const coverageRows = parseCsv(csvText);
const missingRows = coverageRows.filter((row) => row.citation_added_to_review_ttl !== "yes");
const grouped = new Map();

for (const row of missingRows) {
  const ontology = row.native_source_ontology_id;
  if (!grouped.has(ontology)) grouped.set(ontology, []);
  grouped.get(ontology).push(row);
}

const ontologyRows = [...grouped.entries()]
  .map(([ontology, rows]) => {
    const suggestion = suggestions[ontology.toUpperCase()] ?? {};
    return {
      native_source_ontology_id: ontology,
      row_count: rows.length,
      matched_terms: uniqueSorted(rows.map((row) => row.term)).join("; "),
      certainty_assessment: suggestion.certainty_assessment ?? "",
      suggested_paper_title: suggestion.suggested_paper_title ?? "",
      suggested_doi: suggestion.suggested_doi ?? "",
      suggested_pmid: suggestion.suggested_pmid ?? "",
      suggested_year: suggestion.suggested_year ?? "",
      suggested_venue: suggestion.suggested_venue ?? "",
      suggested_url: suggestion.suggested_url ?? "",
      suggested_search_query: `${ontology} ontology disease modelling`,
      action_note: "Verify the suggested paper; if suitable, mark certainty as correct in the DOI workbook.",
      preferred_labels: uniqueSorted(rows.map((row) => row.preferred_label)).join("; "),
      class_iris: uniqueSorted(rows.map((row) => row.class_iri)).join("; "),
    };
  })
  .sort((a, b) => a.native_source_ontology_id.localeCompare(b.native_source_ontology_id));

const classRows = missingRows
  .map((row) => ({
    ...suggestions[row.native_source_ontology_id.toUpperCase()],
    native_source_ontology_id: row.native_source_ontology_id,
    term: row.term,
    preferred_label: row.preferred_label,
    class_iri: row.class_iri,
    citation_status: "needs approved citation",
  }))
  .sort((a, b) =>
    a.native_source_ontology_id.localeCompare(b.native_source_ontology_id) ||
    a.term.localeCompare(b.term) ||
    a.class_iri.localeCompare(b.class_iri),
  );

const summaryRows = [
  { metric: "Generated from", value: inputCsv },
  { metric: "Suggested citations from", value: suggestionPayload.source_workbook },
  { metric: "Independent/native ontologies in citation scope", value: uniqueSorted(coverageRows.map((row) => row.native_source_ontology_id)).length },
  { metric: "Ontologies already cited", value: uniqueSorted(coverageRows.filter((row) => row.citation_added_to_review_ttl === "yes").map((row) => row.native_source_ontology_id)).length },
  { metric: "Ontologies still needing citation", value: ontologyRows.length },
  { metric: "Class rows still needing citation", value: classRows.length },
  { metric: "Rule", value: "Only native disease/injury/condition class rows without an approved citation are listed." },
];

const workbook = Workbook.create();
const summary = workbook.worksheets.add("Summary");
const ontologies = workbook.worksheets.add("Ontologies needing citation");
const classes = workbook.worksheets.add("Class rows");

const summaryColumns = [
  { key: "metric", header: "Metric" },
  { key: "value", header: "Value" },
];
const ontologyColumns = [
  { key: "native_source_ontology_id", header: "Ontology ID" },
  { key: "row_count", header: "Class rows" },
  { key: "matched_terms", header: "Matched terms" },
  { key: "certainty_assessment", header: "Certainty assessment" },
  { key: "suggested_paper_title", header: "Suggested paper title" },
  { key: "suggested_doi", header: "Suggested DOI" },
  { key: "suggested_pmid", header: "Suggested PMID" },
  { key: "suggested_year", header: "Suggested year" },
  { key: "suggested_venue", header: "Suggested venue" },
  { key: "suggested_url", header: "Suggested URL" },
  { key: "suggested_search_query", header: "Suggested search query" },
  { key: "action_note", header: "Action note" },
  { key: "class_iris", header: "Class IRIs" },
];
const classColumns = [
  { key: "native_source_ontology_id", header: "Ontology ID" },
  { key: "term", header: "Term" },
  { key: "preferred_label", header: "Preferred label" },
  { key: "class_iri", header: "Class IRI" },
  { key: "certainty_assessment", header: "Certainty assessment" },
  { key: "suggested_paper_title", header: "Suggested paper title" },
  { key: "suggested_doi", header: "Suggested DOI" },
  { key: "suggested_pmid", header: "Suggested PMID" },
  { key: "suggested_url", header: "Suggested URL" },
];

writeMatrix(summary, matrixFromObjects(summaryRows, summaryColumns));
writeMatrix(ontologies, matrixFromObjects(ontologyRows, ontologyColumns));
writeMatrix(classes, matrixFromObjects(classRows, classColumns));

formatSheet(summary, summaryRows.length + 1, summaryColumns.length, "Summary");
formatSheet(ontologies, ontologyRows.length + 1, ontologyColumns.length, "Ontologies needing citation");
formatSheet(classes, classRows.length + 1, classColumns.length, "Class rows");

const check = await workbook.inspect({
  kind: "table",
  sheetId: "Ontologies needing citation",
  range: "A1:L12",
  include: "values",
  tableMaxRows: 12,
  tableMaxCols: 12,
});
console.log(check.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "formula error scan",
});
console.log(errors.ndjson);

await workbook.render({ sheetName: "Ontologies needing citation", range: "A1:L20", scale: 1 });

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputXlsx);
console.log(outputXlsx);
