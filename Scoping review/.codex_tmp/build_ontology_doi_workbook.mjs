import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve("..");
const tableDir = path.join(root, "Extraction Tables");
const inputPath = path.join(tableDir, "ontology_modelling_paper_doi_lookup.json");
const outputPath = path.join(tableDir, "Ontology_Modelling_Paper_DOIs.xlsx");
const qaDir = path.join(root, ".codex_tmp", "qa");
await fs.mkdir(qaDir, { recursive: true });

const payload = JSON.parse(await fs.readFile(inputPath, "utf8"));

const workbook = Workbook.create();

function asMatrix(rows, headers) {
  return [headers].concat(rows.map((row) => headers.map((header) => row[header] ?? "")));
}

function colName(index) {
  let n = index + 1;
  let name = "";
  while (n > 0) {
    const rem = (n - 1) % 26;
    name = String.fromCharCode(65 + rem) + name;
    n = Math.floor((n - 1) / 26);
  }
  return name;
}

function addSheet(name, headers, rows, widths = {}) {
  const sheet = workbook.worksheets.add(name);
  sheet.showGridLines = false;
  const matrix = asMatrix(rows, headers);
  const end = `${colName(headers.length - 1)}${matrix.length}`;
  const range = sheet.getRange(`A1:${end}`);
  range.values = matrix;
  const header = sheet.getRange(`A1:${colName(headers.length - 1)}1`);
  header.format.fill.color = "#1F4E78";
  header.format.font.color = "#FFFFFF";
  header.format.font.bold = true;
  header.format.wrapText = true;
  header.format.borders = { preset: "bottom", style: "medium", color: "#A6A6A6" };
  range.format.font.name = "Aptos";
  range.format.font.size = 10;
  range.format.wrapText = true;
  range.format.verticalAlignment = "top";
  sheet.freezePanes.freezeRows(1);
  for (let i = 0; i < headers.length; i++) {
    const width = widths[headers[i]] ?? 18;
    sheet.getRange(`${colName(i)}:${colName(i)}`).format.columnWidth = width;
  }
  sheet.getRange(`A1:${end}`).format.borders = { preset: "outside", style: "thin", color: "#BFBFBF" };
  return sheet;
}

const summaryRows = [
  { metric: "Generated at", value: payload.summary.generated_at },
  { metric: "Input extraction", value: payload.summary.enriched_csv },
  { metric: "Ontology/source IDs included", value: payload.summary.ontology_count },
  { metric: "Publication candidates found", value: payload.summary.candidate_count },
  { metric: "Best matches high/high-registry", value: payload.summary.high_or_registry },
  { metric: "Best matches medium", value: payload.summary.medium },
  { metric: "Best matches low or missing", value: payload.summary.low_or_missing },
  { metric: "Skipped duplicate ontology IDs", value: payload.summary.skipped_duplicate_count },
  {
    metric: "Interpretation note",
    value:
      "Rows marked low_needs_manual_check or needs_manual_check_no_candidate should be manually verified before use as canonical ontology-modelling citations.",
  },
];

addSheet("Summary", ["metric", "value"], summaryRows, { metric: 34, value: 110 });

const bestHeaders = [
  "ontology_id",
  "ontology_title",
  "source_databases",
  "source_ontology_ids",
  "matched_class_count",
  "matched_terms",
  "best_doi",
  "best_publication_title",
  "authors",
  "year",
  "venue",
  "publication_url",
  "match_confidence",
  "match_score",
  "lookup_source",
  "lookup_query",
  "review_note",
  "ontology_homepage",
  "ontology_repository",
  "registry_publication_urls",
  "ontology_description",
];
addSheet("Best DOI by Ontology", bestHeaders, payload.best_rows, {
  ontology_id: 16,
  ontology_title: 34,
  source_databases: 22,
  source_ontology_ids: 36,
  matched_class_count: 14,
  matched_terms: 18,
  best_doi: 24,
  best_publication_title: 48,
  authors: 34,
  year: 10,
  venue: 30,
  publication_url: 38,
  match_confidence: 24,
  match_score: 12,
  lookup_source: 24,
  lookup_query: 38,
  review_note: 36,
  ontology_homepage: 38,
  ontology_repository: 38,
  registry_publication_urls: 38,
  ontology_description: 60,
});

const candidateHeaders = [
  "ontology_id",
  "ontology_title",
  "lookup_source",
  "match_confidence",
  "match_score",
  "doi",
  "publication_title",
  "authors",
  "year",
  "venue",
  "url",
  "query",
  "raw_score",
];
addSheet("Candidate Publications", candidateHeaders, payload.candidate_rows, {
  ontology_id: 16,
  ontology_title: 34,
  lookup_source: 24,
  match_confidence: 24,
  match_score: 12,
  doi: 24,
  publication_title: 52,
  authors: 36,
  year: 10,
  venue: 30,
  url: 42,
  query: 42,
  raw_score: 14,
});

const seedHeaders = [
  "source_workbook",
  "authors",
  "year",
  "title",
  "venue",
  "type",
  "doi",
  "url",
  "category",
  "relevance",
];
addSheet("Seed Literature", seedHeaders, payload.seed_rows, {
  source_workbook: 34,
  authors: 38,
  year: 10,
  title: 52,
  venue: 34,
  type: 24,
  doi: 26,
  url: 42,
  category: 30,
  relevance: 72,
});

addSheet("Skipped Duplicates", ["ontology", "reason"], payload.skipped_duplicates, {
  ontology: 18,
  reason: 70,
});

const errorScan = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "formula error scan",
});
console.log(errorScan.ndjson);

const tableCheck = await workbook.inspect({
  kind: "table",
  sheetId: "Best DOI by Ontology",
  range: "A1:H8",
  include: "values",
  tableMaxRows: 8,
  tableMaxCols: 8,
});
console.log(tableCheck.ndjson);

for (const sheetName of ["Summary", "Best DOI by Ontology", "Candidate Publications", "Seed Literature", "Skipped Duplicates"]) {
  const preview = await workbook.render({ sheetName, range: "A1:H20", scale: 1, format: "png" });
  const bytes = new Uint8Array(await preview.arrayBuffer());
  await fs.writeFile(path.join(qaDir, `${sheetName.replaceAll(" ", "_")}.png`), bytes);
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`Saved ${outputPath}`);
