import fs from "node:fs/promises";
import { Workbook } from "@oai/artifact-tool";

const sourcePath = new URL("../../Scoping review/Extraction Tables/disease_terms_review_enriched.csv", import.meta.url);
const target = String(process.argv[2] ?? "PATEL").toUpperCase();
const outputName = String(process.argv[3] ?? "patel_before.png");
const csvText = await fs.readFile(sourcePath, "utf8");
const workbook = await Workbook.fromCSV(csvText, { sheetName: "Review" });
const sheet = workbook.worksheets.getItem("Review");
const values = sheet.getUsedRange(true).values;
const headers = values[0].map((value) => String(value ?? ""));
const index = Object.fromEntries(headers.map((header, position) => [header, position]));

const selectedFields = [
  "ontology",
  "ontology_title",
  "native_ontology_guess",
  "class_iri",
  "preferred_label",
  "modelling_citation_source_ontology_id",
  "modelling_citation_status",
  "modelling_citation_confidence",
  "modelling_citation_doi",
  "modelling_citation_pmid",
  "modelling_citation_pmcid",
  "modelling_citation_url",
  "modelling_citation_publication_title",
  "modelling_citation_authors",
  "modelling_citation_year",
  "modelling_citation_venue",
  "modelling_citation_bibliographic_citation",
  "modelling_citation_lookup_source",
  "modelling_citation_source",
  "modelling_citation_approved",
  "modelling_citation_assignment_flag",
  "modelling_citation_assignment_flag_reason",
  "modelling_citation_assignment_checked_at",
];

function select(row) {
  return Object.fromEntries(selectedFields.map((field) => [field, String(row[index[field]] ?? "")]));
}

const matching = values.slice(1)
  .filter((row) => String(row[index.ontology] ?? "").toUpperCase() === target)
  .map(select);
const exemplars = values.slice(1)
  .filter((row) => String(row[index.modelling_citation_approved] ?? "").toLowerCase() === "yes")
  .slice(0, 2)
  .map(select);

const preview = workbook.worksheets.add("Citation QA");
const previewRows = [
  [`Citation QA before edit: ${target}`, ""],
  ["Matching records", matching.length],
  ...matching.flatMap((row, rowIndex) => [
    [`Record ${rowIndex + 1}`, ""],
    ...selectedFields.map((field) => [field, row[field]]),
  ]),
];
preview.getRangeByIndexes(0, 0, previewRows.length, 2).values = previewRows;
preview.getRange("A1:B1").format = {
  fill: "#1F4E78",
  font: { bold: true, color: "#FFFFFF" },
};
preview.getRange(`A1:A${previewRows.length}`).format.columnWidth = 34;
preview.getRange(`B1:B${previewRows.length}`).format.columnWidth = 88;
preview.getRange(`A1:B${previewRows.length}`).format.wrapText = true;
preview.freezePanes.freezeRows(1);

const rendered = await workbook.render({
  sheetName: "Citation QA",
  range: `A1:B${previewRows.length}`,
  scale: 1.25,
});
await fs.writeFile(new URL(`./${outputName}`, import.meta.url), Buffer.from(await rendered.arrayBuffer()));

console.log(JSON.stringify({ rowCount: values.length - 1, matching, exemplars }, null, 2));
process.exit(0);
