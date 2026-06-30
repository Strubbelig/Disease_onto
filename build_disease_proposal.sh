#!/usr/bin/env bash
# build_disease_proposal.sh  (revised)
#
# Builds modules for "Disease proposal 2.ttl" from local source ontologies,
# merges the proposal, and runs HermiT consistency checks.
#
# WHAT CHANGED vs. the original (two fixes, marked CHANGED/NEW below):
#
#   FIX 1 — Joint STAR extraction (the soundness fix).
#     The original ran one independent STAR extraction per source, each seeded
#     with only its own namespace bucket. A bridging axiom living in RO about a
#     BFO term reached only transitively through BFO is local w.r.t. the RO seed
#     and gets dropped — so the union of the per-source modules can be consistent
#     while proposal + full-BFO + full-RO is inconsistent. The seam contradiction
#     falls between the modules.
#     Fix: merge ten sources (bfo, ro, iao, obi, ogms, cob, pato, uo, doid, hp)
#     into ONE input and run a SINGLE STAR extraction over the COMBINED seed.
#     The fixpoint then closes across sources, so cross-source bridging axioms
#     are non-local and survive. (GO/ChEBI/DRON remain MIREOT leaf modules;
#     upheno is label-only annotation; see FIX 2 for the closure check.)
#
#   FIX 2 — Full-closure ground-truth reasoning (the decisive check).
#     The original reasoned over proposal + MODULES, which structurally cannot
#     detect a dropped bridging axiom (it isn't in any module). We add a SECOND,
#     separate HermiT run over proposal + the FULL unmodularized sources, and a
#     2x2 verdict comparing it against the modular run. If modular says
#     "consistent" but full-closure says "inconsistent", a bridging axiom was
#     dropped and the modular artifact is unsound.
#
#   Minor: term discovery now uses a full signature scan (subject/predicate/
#   object union) instead of declared-entities-only, so external terms that
#   appear only inside class expressions are not missed.
#
# Usage:
#   bash build_disease_proposal.sh                 # build + merge + BOTH reasons
#   bash build_disease_proposal.sh --no-reason     # skip HermiT (faster)
#   bash build_disease_proposal.sh --stubs         # report remaining stubs
#   bash build_disease_proposal.sh --full-giants   # load FULL go/chebi in the
#                                                  #   ground-truth reason (slow,
#                                                  #   needs RAM; default uses the
#                                                  #   MIREOT leaf modules)
#
# Output:
#   Disease ontology modules/        updated module .owl files
#   Disease proposal 2 merged.owl    fully merged (modular) ontology
 
set -euo pipefail
 
ROBOT="java -Xmx10g -jar /usr/local/bin/robot.jar"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMP="/Users/Strubbelig/Library/Mobile Documents/com~apple~CloudDocs/Forschung/Ontology/Import ontologies"
IMP_WOND="/Users/Strubbelig/Library/Mobile Documents/com~apple~CloudDocs/Forschung/Ontology/Wound ontology/src/ontology/imports"
MODULE_DIR="$SCRIPT_DIR/Disease ontology modules"
GT_OWL="https://bioportal.bioontology.org/ontologies/WONT"
INPUT="$SCRIPT_DIR/Disease proposal 2.ttl"
OUTPUT="$SCRIPT_DIR/Disease proposal 2 merged.owl"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
 
RUN_REASON=true
RUN_STUBS=false
FULL_GIANTS=false
for arg in "$@"; do
  case "$arg" in
    --no-reason)   RUN_REASON=false ;;
    --stubs)       RUN_STUBS=true ;;
    --full-giants) FULL_GIANTS=true ;;
  esac
done
 
# Sources that go through STAR and are merged for the JOINT extraction (FIX 1).
# Order doesn't matter; robot merge dedupes.
STAR_SOURCES=(
  bfo:"$IMP/bfo-core2020.owl"
  ro:"$IMP/ro.owl"
  iao:"$IMP/iao.owl"
  obi:"$IMP/obi.owl"
  ogms:"$IMP/ogms.owl"
  cob:"$IMP/cob.owl"
  pato:"$IMP/pato.owl"
  uo:"$IMP/uo.owl"
  doid:"$IMP/doid.owl"
  hp:"$IMP/hp.obo"
)
# Namespace buckets whose seed terms feed the joint STAR extraction.
STAR_BUCKETS=(bfo ro iao obi ogms cob pato uo doid hp)
 
# ── Step 1: Build a base TTL that only imports ground_truth ────────────────────
echo "[1/5] Creating base (disease proposal with only ground_truth import)..."
python3 - "$INPUT" "$TMP/base.ttl" << 'PYEOF'
import sys, re
with open(sys.argv[1]) as f:
    content = f.read()
new_imports = 'owl:imports <https://bioportal.bioontology.org/ontologies/WONT> .'
content = re.sub(
    r'owl:imports\s+<[^>]+>(?:\s*,\s*<[^>]+>)*\s*\.',
    new_imports, content, flags=re.DOTALL,
)
with open(sys.argv[2], 'w') as f:
    f.write(content)
print("  Base TTL written.")
PYEOF
 
cat > "$TMP/catalog-v001.xml" << 'CATEOF'
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<catalog prefer="public" xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog">
    <uri id="Imports Wizard Entry" name="https://bioportal.bioontology.org/ontologies/WONT"
         uri="file:/Users/Strubbelig/Library/Mobile%20Documents/com~apple~CloudDocs/Forschung/Ontology/Wound%20ontology/data/ground%20truth/ground_truth_final.owl"/>
</catalog>
CATEOF
 
$ROBOT merge --input "$TMP/base.ttl" --output "$TMP/combined_own.owl"
echo "  Combined own content: $(wc -l < "$TMP/combined_own.owl") lines"
 
# ── Step 2: Discover external terms (full signature scan) ──────────────────────
echo "[2/5] Discovering external terms by namespace (signature scan)..."
 
# CHANGED: signature scan over subject/predicate/object, not declared entities
# only — catches terms buried inside restrictions/class expressions.
cat > "$TMP/find_external.sparql" << 'EOF'
SELECT DISTINCT ?term WHERE {
  { ?term ?p ?o } UNION { ?s ?term ?o } UNION { ?s ?p ?term }
  FILTER(isIRI(?term))
  FILTER(!STRSTARTS(STR(?term), "http://www.w3.org/"))
  FILTER(!STRSTARTS(STR(?term), "https://bioportal.bioontology.org/ontologies/MILD"))
  FILTER(!STRSTARTS(STR(?term), "https://bioportal.bioontology.org/ontologies/WONT"))
  FILTER(!STRSTARTS(STR(?term), "http://purl.obolibrary.org/obo/wond"))
}
EOF
 
$ROBOT query --input "$TMP/combined_own.owl" \
  --query "$TMP/find_external.sparql" "$TMP/external_terms.csv" 2>/dev/null
 
python3 - "$TMP" << 'PYEOF'
import csv, sys
scratch = sys.argv[1]
buckets = {k: [] for k in (
    'bfo','ro','iao','obi','ogms','pato','cob','go',
    'hp','chebi','doid','dron','ncbi','uo','upheno')}
with open(f"{scratch}/external_terms.csv") as f:
    for row in csv.DictReader(f):
        iri = row['term'].strip()
        if 'purl.obolibrary.org' not in iri:
            continue
        local = iri.split('/obo/')[-1]
        if   local.startswith('BFO_'):                   buckets['bfo'].append(iri)
        elif local.startswith('RO_'):                    buckets['ro'].append(iri)
        elif local.startswith('IAO_'):                   buckets['iao'].append(iri)
        elif local.startswith(('OBI_','IDO_','OMRSE_')): buckets['obi'].append(iri)
        elif local.startswith('OGMS_'):                  buckets['ogms'].append(iri)
        elif local.startswith('PATO_'):                  buckets['pato'].append(iri)
        elif local.startswith('COB_'):                   buckets['cob'].append(iri)
        elif local.startswith('GO_'):                    buckets['go'].append(iri)
        elif local.startswith('HP_'):                    buckets['hp'].append(iri)
        elif local.startswith('CHEBI_'):                 buckets['chebi'].append(iri)
        elif local.startswith('DOID_'):                  buckets['doid'].append(iri)
        elif local.startswith('DRON_'):                  buckets['dron'].append(iri)
        elif local.startswith('NCBITaxon_'):             buckets['ncbi'].append(iri)
        elif local.startswith('UO_'):                    buckets['uo'].append(iri)
        elif local.startswith('UPHENO_'):                buckets['upheno'].append(iri)
for name, iris in buckets.items():
    with open(f"{scratch}/termfile_{name}.txt", 'w') as f:
        f.write('\n'.join(iris) + ('\n' if iris else ''))
    print(f"  {name:10s} {len(iris):3d} terms")
# RO_0002314 needed by UPHENO equivalentClass, not referenced directly.
with open(f"{scratch}/termfile_ro.txt", 'a') as f:
    f.write("http://purl.obolibrary.org/obo/RO_0002314\n")
PYEOF
 
# ── Step 3: JOINT STAR extraction over merged upper/mid sources ────────────────
# ── CHANGED ── one merge + one STAR, replacing per-source extractions.
echo "[3/5] Joint STAR extraction (merged bfo+ro+iao+obi+ogms+cob+pato+uo+doid+hp)..."
 
# 3a. Build the combined seed (union of the six STAR buckets).
: > "$TMP/seed_core.txt"
for b in "${STAR_BUCKETS[@]}"; do
  [[ -s "$TMP/termfile_${b}.txt" ]] && cat "$TMP/termfile_${b}.txt" >> "$TMP/seed_core.txt"
done
sort -u "$TMP/seed_core.txt" -o "$TMP/seed_core.txt"
echo "  combined seed: $(wc -l < "$TMP/seed_core.txt" | tr -d ' ') terms"
 
# 3b. Merge the six sources into one input so the STAR fixpoint can close
#     ACROSS sources (this is what preserves cross-source bridging axioms).
core_merge_args=()
for entry in "${STAR_SOURCES[@]}"; do
  src="${entry#*:}"
  [[ -f "$src" ]] && core_merge_args+=(--input "$src") \
                  || echo "  [warn] missing STAR source: $src"
done
$ROBOT merge "${core_merge_args[@]}" --output "$TMP/sources_core.owl" 2>/dev/null
echo "  merged STAR sources: $(wc -l < "$TMP/sources_core.owl" | tr -d ' ') lines"
 
# 3c. Single STAR extraction over the merged sources + combined seed.
$ROBOT extract --method STAR --input "$TMP/sources_core.owl" \
  --term-file "$TMP/seed_core.txt" \
  --output "$TMP/extract_core.owl" 2>/dev/null
echo "  extract_core: $(wc -l < "$TMP/extract_core.owl" | tr -d ' ') lines"
 
# UPHENO: filter (annotation-only; root class with many descendants we don't seed).
if [[ -s "$TMP/termfile_upheno.txt" ]]; then
  $ROBOT filter --input "$IMP/upheno.owl" \
    --term "http://purl.obolibrary.org/obo/UPHENO_0001001" \
    --select "self annotations" --output "$TMP/extract_upheno.owl" 2>/dev/null
  echo "  extract_upheno: $(wc -l < "$TMP/extract_upheno.owl" | tr -d ' ') lines"
fi
 
# NCBITaxon: convert micro.obo (5 taxa) + add NCBITaxon_9606 (Homo sapiens).
if [[ -s "$TMP/termfile_ncbi.txt" ]]; then
  $ROBOT convert --input "$IMP/ncbitaxon_micro.obo" \
    --output "$TMP/ncbitaxon_micro_owl.owl" 2>/dev/null
  cat > "$TMP/ncbitaxon_9606.owl" << 'OWLEOF'
<?xml version="1.0"?>
<rdf:RDF xmlns:obo="http://purl.obolibrary.org/obo/"
     xmlns:owl="http://www.w3.org/2002/07/owl#"
     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
     xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">
    <owl:Ontology rdf:about="http://purl.obolibrary.org/obo/wond/modules/ncbitaxon_9606_tmp.owl"/>
    <owl:Class rdf:about="http://purl.obolibrary.org/obo/NCBITaxon_9606">
        <rdfs:label xml:lang="en">Homo sapiens</rdfs:label>
        <obo:IAO_0000115 xml:lang="en">The species Homo sapiens (human).</obo:IAO_0000115>
    </owl:Class>
</rdf:RDF>
OWLEOF
  $ROBOT merge --input "$TMP/ncbitaxon_micro_owl.owl" \
    --input "$TMP/ncbitaxon_9606.owl" \
    --output "$TMP/extract_ncbi.owl" 2>/dev/null
  echo "  extract_ncbi: $(wc -l < "$TMP/extract_ncbi.owl" | tr -d ' ') lines"
fi
 
# ── Step 4: Assemble modules with wond/modules/ IRIs ───────────────────────────
echo "[4/5] Assembling modules with wond/modules/ IRIs..."
 
make_module() {  # merge inputs -> re-IRI -> strip versionIRI
  local name="$1"; shift
  local out="$MODULE_DIR/${name}_module.owl"
  local tmp_out="$TMP/${name}_module_tmp.owl"
  local merge_args=()
  for f in "$@"; do [[ -f "$f" ]] && merge_args+=(--input "$f"); done
  [[ ${#merge_args[@]} -eq 0 ]] && echo "  [skip] ${name}_module (no inputs)" && return 0
  $ROBOT merge "${merge_args[@]}" --output "$tmp_out" 2>/dev/null
  $ROBOT annotate --input "$tmp_out" \
    --ontology-iri "http://purl.obolibrary.org/obo/wond/modules/${name}_module.owl" \
    --output "$out" 2>/dev/null
  sed -i '' '/<owl:versionIRI/d' "$out"
  echo "  ${name}_module.owl: $(wc -l < "$out" | tr -d ' ') lines"
}
 
# ── NEW ── label-only module carved from the joint extract, so the existing
# per-namespace module files still exist for the catalog while ALL logical
# content (incl. cross-source bridging axioms) lives in obi_module via
# extract_core. Union of modules == joint extract; nothing is lost or split.
make_label_module() {
  local name="$1"
  local termfile="$TMP/termfile_${name}.txt"
  local out="$MODULE_DIR/${name}_module.owl"
  [[ ! -s "$termfile" ]] && echo "  [skip] ${name}_module (no terms)" && return 0
  $ROBOT filter --input "$TMP/extract_core.owl" \
    --term-file "$termfile" --select "self annotations" \
    --output "$TMP/label_${name}.owl" 2>/dev/null
  $ROBOT annotate --input "$TMP/label_${name}.owl" \
    --ontology-iri "http://purl.obolibrary.org/obo/wond/modules/${name}_module.owl" \
    --output "$out" 2>/dev/null
  sed -i '' '/<owl:versionIRI/d' "$out"
  echo "  ${name}_module.owl: $(wc -l < "$out" | tr -d ' ') lines (labels; logic in obi_module)"
}
 
# ── CHANGED ── obi_module now carries the WHOLE joint extract (all six STAR
# sources), not four separate per-source extracts.
make_module obi \
  "$IMP_WOND/obi_import.owl" \
  "$TMP/extract_core.owl"
 
# ogms/cob/pato/uo/doid/hp: label-carriers; all logic is in extract_core.
make_label_module ogms
make_label_module cob
make_label_module pato
make_label_module uo
make_label_module doid
make_label_module hp

make_module upheno    "$TMP/extract_upheno.owl"
make_module ncbitaxon "$TMP/extract_ncbi.owl"
for ns in go chebi dron; do
  make_module "$ns" "$IMP_WOND/${ns}_import.owl"
done
 
echo "Modules written to: $MODULE_DIR/"
 
# ── Merge disease proposal (modular artifact) ──────────────────────────────────
echo ""
echo "Merging disease proposal with modules..."
$ROBOT merge --input "$INPUT" --output "$OUTPUT" 2>&1 | grep -v "^$\|INFO" || true
echo "Merged → $OUTPUT ($(wc -l < "$OUTPUT" | tr -d ' ') lines, $(du -sh "$OUTPUT" | cut -f1))"
 
# ── Step 5: Reasoning — modular AND full-closure ground truth ──────────────────
# Helper: run HermiT, return 0 if consistent/satisfiable, 1 otherwise.
# (Called inside `if`, so set -e is suspended for the inner robot call.)
run_reason() {
  local label="$1" input="$2"
  $ROBOT reason --input "$input" --reasoner hermit \
    --output "$TMP/reasoned_${label}.owl" > "$TMP/reason_${label}.log" 2>&1
}
 
if $RUN_REASON; then
  echo ""
  echo "[5/5] Reasoning..."
 
  # (a) Modular artifact: proposal + the lean modules.
  echo "  → modular (proposal + modules)..."
  if run_reason modular "$OUTPUT"; then MOD_OK=1; else MOD_OK=0; fi
 
  # ── NEW ── (b) Ground truth: proposal own content + FULL unmodularized
  # sources. This is the only run that can reveal a dropped bridging axiom.
  echo "  → full-closure ground truth (proposal + FULL sources)..."
  gt_args=(--input "$TMP/combined_own.owl")
  # Full upper/mid sources (logically rich; where seams actually occur).
  for f in \
      "$IMP/bfo-core2020.owl" "$IMP/ro.owl" "$IMP/iao.owl" "$IMP/obi.owl" \
      "$IMP/cob.owl" "$IMP/ogms.owl" "$IMP/pato.owl" "$IMP/uo.owl" \
      "$IMP/upheno.owl"; do
    [[ -f "$f" ]] && gt_args+=(--input "$f")
  done
  gt_args+=(--input "$TMP/extract_ncbi.owl")
 
  # Leaf giants: MIREOT modules by default (tractable); full with --full-giants.
  if $FULL_GIANTS; then
    [[ -f "$IMP/go.owl" ]]    && gt_args+=(--input "$IMP/go.owl")
    if   [[ -f "$IMP/chebi.owl" ]]; then gt_args+=(--input "$IMP/chebi.owl")
    elif [[ -f "$IMP/chebi.obo" ]]; then
      $ROBOT convert --input "$IMP/chebi.obo" --output "$TMP/chebi_full.owl" 2>/dev/null
      gt_args+=(--input "$TMP/chebi_full.owl")
    fi
    GIANTS_NOTE="go,chebi=FULL"
  else
    for ns in go chebi; do
      [[ -f "$IMP_WOND/${ns}_import.owl" ]] && gt_args+=(--input "$IMP_WOND/${ns}_import.owl")
    done
    GIANTS_NOTE="go,chebi=MIREOT (use --full-giants for full)"
  fi
  # DOID/HP: full local sources available; use them.
  [[ -f "$IMP/doid.owl" ]] && gt_args+=(--input "$IMP/doid.owl")
  [[ -f "$IMP/hp.obo"   ]] && gt_args+=(--input "$IMP/hp.obo")
  # DRON: no full local source — MIREOT only (acknowledged gap).
  [[ -f "$IMP_WOND/dron_import.owl" ]] && gt_args+=(--input "$IMP_WOND/dron_import.owl")

  $ROBOT merge "${gt_args[@]}" --output "$TMP/ground_truth_merge.owl" 2>/dev/null
  echo "    closure merged: $(wc -l < "$TMP/ground_truth_merge.owl" | tr -d ' ') lines  [$GIANTS_NOTE; doid,hp=FULL; dron=MIREOT]"
  if run_reason groundtruth "$TMP/ground_truth_merge.owl"; then GT_OK=1; else GT_OK=0; fi
 
  # ── Verdict (2x2) ────────────────────────────────────────────────────────────
  echo ""
  echo "  ┌─ consistency verdict ─────────────────────────────────────────────"
  if   [[ $MOD_OK -eq 1 && $GT_OK -eq 1 ]]; then
    echo "  │ SAFE.  Modular and full closure agree: both CONSISTENT."
    echo "  │ The lean modules are a sound stand-in for the full imports"
    echo "  │ (within the closure checked; dron only via MIREOT)."
  elif [[ $MOD_OK -eq 1 && $GT_OK -eq 0 ]]; then
    echo "  │ ⚠ SEAM DETECTED.  Modules CONSISTENT but full closure INCONSISTENT."
    echo "  │ A bridging axiom was dropped during extraction — the modular"
    echo "  │ artifact is UNSOUND. The killing axiom lives in a source whose"
    echo "  │ logical link was local w.r.t. the per-namespace seed. Fold that"
    echo "  │ source into the joint STAR extraction (STAR_SOURCES), or widen"
    echo "  │ the seed. See: $TMP/reason_groundtruth.log"
  elif [[ $MOD_OK -eq 0 && $GT_OK -eq 0 ]]; then
    echo "  │ GENUINE INCONSISTENCY.  Both runs inconsistent — the problem is in"
    echo "  │ your own content, not a seam artifact. Fix the modeling."
    echo "  │ See: $TMP/reason_modular.log"
  else
    echo "  │ MODULE BUG.  Modules INCONSISTENT but full closure CONSISTENT —"
    echo "  │ unexpected. Likely a module-construction fault (bad re-IRI,"
    echo "  │ duplicated/mangled axiom, broken import). Inspect the modules."
    echo "  │ See: $TMP/reason_modular.log"
  fi
  echo "  └───────────────────────────────────────────────────────────────────"
fi
 
# ── Stub report ───────────────────────────────────────────────────────────────
if $RUN_STUBS; then
  echo ""
  echo "Stub report (terms with no label)..."
  cat > "$TMP/stubs.sparql" << 'EOF'
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT ?term WHERE {
  { ?term a owl:Class . } UNION { ?term a owl:ObjectProperty . }
  FILTER(!isBlank(?term))
  FILTER(!STRSTARTS(STR(?term), "http://www.w3.org/"))
  FILTER NOT EXISTS { ?term rdfs:label ?l }
  FILTER NOT EXISTS { ?term obo:IAO_0000111 ?l2 }
  FILTER NOT EXISTS { ?term obo:BFO_0000179 ?l3 }
  FILTER NOT EXISTS { ?term owl:deprecated true }
} ORDER BY ?term
EOF
  STUBS_OUT="$TMP/stubs_out.csv"
  $ROBOT query --input "$OUTPUT" --query "$TMP/stubs.sparql" "$STUBS_OUT" 2>/dev/null
  count=$(grep -c "." "$STUBS_OUT" 2>/dev/null || echo 0)
  echo "  $((count - 1)) stubs found:"
  grep -v "^term$" "$STUBS_OUT" | head -30 || true
  echo "  (NB: 'has a label' is not 'logically complete' — a labelled term can"
  echo "   still be missing the axiom that would make it interfere. Trust the"
  echo "   ground-truth verdict above, not the stub count, for soundness.)"
fi
 
echo ""
echo "Done."