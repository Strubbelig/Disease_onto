import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve("..");
const tableDir = path.join(root, "Extraction Tables");
const inputPath = path.join(tableDir, "ontology_modelling_paper_doi_lookup.json");
const pubmedInputPath = path.join(tableDir, "ontology_pubmed_acronym_ontology_lookup.json");
const pubmedFullNameInputPath = path.join(tableDir, "ontology_pubmed_fullname_ontology_lookup.json");
const mergedInputPath = path.join(tableDir, "ontology_merged_best_fit_lookup.json");
const appearanceRoutesInputPath = path.join(tableDir, "ontology_source_appearance_routes_summary.json");
const outputPath = path.join(tableDir, "Ontology_Modelling_Paper_DOIs.xlsx");
const qaDir = path.join(root, ".codex_tmp", "qa");
await fs.mkdir(qaDir, { recursive: true });

const payload = JSON.parse(await fs.readFile(inputPath, "utf8"));
let pubmedPayload = { summary: {}, best_rows: [], result_rows: [] };
let pubmedFullNamePayload = { summary: {}, best_rows: [], result_rows: [] };
let mergedPayload = { summary: {}, merged_best_rows: [], merged_candidate_rows: [] };
let appearanceRoutes = [];
try {
  pubmedPayload = JSON.parse(await fs.readFile(pubmedInputPath, "utf8"));
} catch {
  pubmedPayload = { summary: {}, best_rows: [], result_rows: [] };
}
try {
  pubmedFullNamePayload = JSON.parse(await fs.readFile(pubmedFullNameInputPath, "utf8"));
} catch {
  pubmedFullNamePayload = { summary: {}, best_rows: [], result_rows: [] };
}
try {
  mergedPayload = JSON.parse(await fs.readFile(mergedInputPath, "utf8"));
} catch {
  mergedPayload = { summary: {}, merged_best_rows: [], merged_candidate_rows: [] };
}
try {
  appearanceRoutes = JSON.parse(await fs.readFile(appearanceRoutesInputPath, "utf8"));
} catch {
  appearanceRoutes = [];
}

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
  { metric: "PubMed query pattern", value: pubmedPayload.summary.query_pattern ?? "" },
  { metric: "PubMed ontologies with hits", value: pubmedPayload.summary.ontologies_with_pubmed_hits ?? "" },
  { metric: "PubMed top hits with DOI", value: pubmedPayload.summary.ontologies_with_pubmed_doi_on_top_hit ?? "" },
  { metric: "PubMed result rows", value: pubmedPayload.summary.pubmed_result_rows ?? "" },
  { metric: "PubMed full-name query pattern", value: pubmedFullNamePayload.summary.query_pattern ?? "" },
  { metric: "PubMed full-name ontologies with hits", value: pubmedFullNamePayload.summary.ontologies_with_pubmed_hits ?? "" },
  { metric: "Merged best-fit high", value: mergedPayload.summary.high ?? "" },
  { metric: "Merged best-fit medium", value: mergedPayload.summary.medium ?? "" },
  { metric: "Merged best-fit low/very-low/missing", value: ((mergedPayload.summary.low_screen ?? 0) + (mergedPayload.summary.very_low_or_missing ?? 0)) || "" },
  { metric: "Dependency-only rows with no separate citation needed", value: mergedPayload.summary.dependency_only_no_citation_needed ?? "" },
  {
    metric: "Interpretation note",
    value:
      "Use 'Merged Best Fit' first. Rows below high confidence should be manually verified before use as canonical ontology-modelling citations. PubMed acronym sheets use only the simple query 'ACRONYM ontology'; full-name sheets use the ontology title plus ontology.",
  },
];

addSheet("Summary", ["metric", "value"], summaryRows, { metric: 34, value: 110 });

const mergedBestHeaders = [
  "ontology_id",
  "ontology_title",
  "source_databases",
  "matched_class_count",
  "matched_terms",
  "best_fit_confidence",
  "best_fit_score",
  "ontology_review_route",
  "depends_on_ontology_ids",
  "doi",
  "pmid",
  "pmcid",
  "publication_title",
  "authors",
  "year",
  "venue",
  "url",
  "doi_url",
  "best_source_family",
  "lookup_source",
  "query_mode",
  "query",
  "pubmed_total_count",
  "rank",
  "title_exact_or_substring_match",
  "ontology_title_token_overlap",
  "title_has_model_word",
  "screening_note",
  "route_recommendation",
  "ontology_homepage",
  "ontology_repository",
];
addSheet("Merged Best Fit", mergedBestHeaders, mergedPayload.merged_best_rows, {
  ontology_id: 16,
  ontology_title: 34,
  source_databases: 22,
  matched_class_count: 14,
  matched_terms: 18,
  best_fit_confidence: 20,
  best_fit_score: 12,
  ontology_review_route: 30,
  depends_on_ontology_ids: 22,
  doi: 24,
  pmid: 14,
  pmcid: 16,
  publication_title: 54,
  authors: 38,
  year: 10,
  venue: 28,
  url: 42,
  doi_url: 36,
  best_source_family: 20,
  lookup_source: 24,
  query_mode: 20,
  query: 42,
  pubmed_total_count: 12,
  rank: 8,
  title_exact_or_substring_match: 16,
  ontology_title_token_overlap: 12,
  title_has_model_word: 14,
  screening_note: 44,
  route_recommendation: 54,
  ontology_homepage: 38,
  ontology_repository: 38,
});

const appearanceRouteHeaders = [
  "source_database",
  "source_ontology_id",
  "source_ontology_title",
  "terms_seen",
  "class_count",
  "native_class_count",
  "imported_dependency_class_count",
  "unknown_namespace_class_count",
  "depends_on_ontology_ids",
  "ontology_review_route",
  "recommendation",
  "class_iris",
];
addSheet("Source Appearance Routes", appearanceRouteHeaders, appearanceRoutes, {
  source_database: 18,
  source_ontology_id: 18,
  source_ontology_title: 38,
  terms_seen: 18,
  class_count: 12,
  native_class_count: 14,
  imported_dependency_class_count: 18,
  unknown_namespace_class_count: 18,
  depends_on_ontology_ids: 22,
  ontology_review_route: 34,
  recommendation: 62,
  class_iris: 70,
});

const mergedCandidateHeaders = [
  "ontology_id",
  "ontology_title",
  "source_family",
  "best_fit_confidence",
  "best_fit_score",
  "source_priority",
  "doi",
  "pmid",
  "publication_title",
  "authors",
  "year",
  "venue",
  "url",
  "lookup_source",
  "query_mode",
  "query",
  "pubmed_total_count",
  "rank",
  "title_exact_or_substring_match",
  "ontology_title_token_overlap",
  "title_has_model_word",
  "screening_note",
];
addSheet("Merged Candidates", mergedCandidateHeaders, mergedPayload.merged_candidate_rows, {
  ontology_id: 16,
  ontology_title: 34,
  source_family: 20,
  best_fit_confidence: 20,
  best_fit_score: 12,
  source_priority: 12,
  doi: 24,
  pmid: 14,
  publication_title: 54,
  authors: 38,
  year: 10,
  venue: 28,
  url: 42,
  lookup_source: 24,
  query_mode: 20,
  query: 42,
  pubmed_total_count: 12,
  rank: 8,
  title_exact_or_substring_match: 16,
  ontology_title_token_overlap: 12,
  title_has_model_word: 14,
  screening_note: 44,
});

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

const pubmedHeaders = [
  "ontology_id",
  "ontology_title",
  "pubmed_query",
  "pubmed_total_count",
  "rank",
  "pmid",
  "doi",
  "pmcid",
  "title",
  "authors",
  "journal",
  "pubdate",
  "pubtypes",
  "pubmed_url",
  "doi_url",
  "query_translation",
  "note",
];
addSheet("PubMed Top Hit", pubmedHeaders, pubmedPayload.best_rows, {
  ontology_id: 16,
  ontology_title: 34,
  pubmed_query: 22,
  pubmed_total_count: 12,
  rank: 8,
  pmid: 14,
  doi: 24,
  pmcid: 16,
  title: 54,
  authors: 42,
  journal: 24,
  pubdate: 14,
  pubtypes: 28,
  pubmed_url: 36,
  doi_url: 36,
  query_translation: 42,
  note: 50,
});

addSheet("PubMed All Results", pubmedHeaders, pubmedPayload.result_rows, {
  ontology_id: 16,
  ontology_title: 34,
  pubmed_query: 22,
  pubmed_total_count: 12,
  rank: 8,
  pmid: 14,
  doi: 24,
  pmcid: 16,
  title: 54,
  authors: 42,
  journal: 24,
  pubdate: 14,
  pubtypes: 28,
  pubmed_url: 36,
  doi_url: 36,
  query_translation: 42,
  note: 50,
});

const pubmedFullNameHeaders = [
  "ontology_id",
  "ontology_title",
  "pubmed_query",
  "query_mode",
  "pubmed_total_count",
  "rank",
  "pmid",
  "doi",
  "pmcid",
  "title",
  "authors",
  "journal",
  "pubdate",
  "pubtypes",
  "pubmed_url",
  "doi_url",
  "query_translation",
  "note",
];
addSheet("PubMed Full Name Top Hit", pubmedFullNameHeaders, pubmedFullNamePayload.best_rows, {
  ontology_id: 16,
  ontology_title: 34,
  pubmed_query: 42,
  query_mode: 20,
  pubmed_total_count: 12,
  rank: 8,
  pmid: 14,
  doi: 24,
  pmcid: 16,
  title: 54,
  authors: 42,
  journal: 24,
  pubdate: 14,
  pubtypes: 28,
  pubmed_url: 36,
  doi_url: 36,
  query_translation: 42,
  note: 50,
});

addSheet("PubMed Full Name All", pubmedFullNameHeaders, pubmedFullNamePayload.result_rows, {
  ontology_id: 16,
  ontology_title: 34,
  pubmed_query: 42,
  query_mode: 20,
  pubmed_total_count: 12,
  rank: 8,
  pmid: 14,
  doi: 24,
  pmcid: 16,
  title: 54,
  authors: 42,
  journal: 24,
  pubdate: 14,
  pubtypes: 28,
  pubmed_url: 36,
  doi_url: 36,
  query_translation: 42,
  note: 50,
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

for (const sheetName of [
  "Summary",
  "Merged Best Fit",
  "Source Appearance Routes",
  "Merged Candidates",
  "Best DOI by Ontology",
  "Candidate Publications",
  "PubMed Full Name Top Hit",
  "PubMed Full Name All",
  "PubMed Top Hit",
  "PubMed All Results",
  "Seed Literature",
  "Skipped Duplicates",
]) {
  const preview = await workbook.render({ sheetName, range: "A1:H20", scale: 1, format: "png" });
  const bytes = new Uint8Array(await preview.arrayBuffer());
  await fs.writeFile(path.join(qaDir, `${sheetName.replaceAll(" ", "_")}.png`), bytes);
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`Saved ${outputPath}`);
