import fs from "node:fs/promises";
import { Workbook } from "@oai/artifact-tool";

const source = "Scoping review/Extraction Tables/disease_terms_review_enriched.csv";
const outDir = ".codex_tmp/spreadsheet_qa";
const csvText = await fs.readFile(source, "utf8");
const workbook = await Workbook.fromCSV(csvText, { sheetName: "Master" });
const sheet = workbook.worksheets.getItem("Master");
const used = sheet.getUsedRange();
const values = used.values;
const headers = values[0].map((value) => String(value ?? ""));

function columnName(index) {
  let value = index + 1;
  let name = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    name = String.fromCharCode(65 + remainder) + name;
    value = Math.floor((value - 1) / 26);
  }
  return name;
}

const keyHeaders = [
  "class_iri",
  "effective_synthesis_status",
  "hierarchy_evidence_status",
  "publication_ambiguity_flags",
  "modelling_citation_approved",
];
const positions = Object.fromEntries(
  keyHeaders.map((header) => [header, headers.indexOf(header)]),
);
console.log(JSON.stringify({ rows: values.length, columns: headers.length, positions }));

const overview = await workbook.inspect({
  kind: "table",
  range: "Master!A1:M8",
  include: "values,formulas",
  tableMaxRows: 8,
  tableMaxCols: 13,
  tableMaxCellChars: 90,
  maxChars: 5000,
});
console.log(overview.ndjson);

const publicationIndexes = keyHeaders.slice(1).map((header) => positions[header]);
const start = Math.max(0, Math.min(...publicationIndexes) - 1);
const end = Math.min(headers.length - 1, Math.max(...publicationIndexes) + 1);
const publicationRange = `${columnName(start)}1:${columnName(end)}8`;
const publication = await workbook.inspect({
  kind: "table",
  range: `Master!${publicationRange}`,
  include: "values,formulas",
  tableMaxRows: 8,
  tableMaxCols: end - start + 1,
  tableMaxCellChars: 90,
  maxChars: 7000,
});
console.log(publication.ndjson);

const preview = await workbook.render({
  sheetName: "Master",
  range: "A1:M10",
  scale: 1.25,
  format: "png",
});
await fs.writeFile(`${outDir}/master_preview.png`, new Uint8Array(await preview.arrayBuffer()));
