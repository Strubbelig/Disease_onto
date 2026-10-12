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
#   FIX 3 (2026-09-12) — the over-extracted obi_module.
#     With full pato.owl inside the joint merge, the STAR fixpoint ran away:
#     16.3 MB, 5 549 classes, 29 roots beside `entity` (2 470 GO, 1 268 UBERON,
#     529 UO, 334 CL, 330 CHEBI, 135 DOID, 38 SYMP ...), none of it referenced
#     by WONT or MILD. Measured 2026-09-12: the six upper sources alone give a
#     0.9 MB module; adding full pato.owl to the merge gives 15.2 MB; adding
#     full uo.owl gives 1.4 MB (all 518 units, because `unit` is seeded).
#     Fix, three parts:
#       (a) PATO is BOT-extracted ON ITS OWN first (66 KB) and that
#           module joins the joint merge in place of full pato.owl. The joint
#           fixpoint still closes across BFO/RO/IAO/OBI/OGMS/COB and the PATO
#           axioms that matter; only PATO's bundled GO/UBERON/CHEBI logic is
#           kept out.
#       (b) UO is a label-only stub for `unit` (the single UO term in use);
#           its 518 subclasses are not.
#       (c) DOID and HP are MIREOT paths (seed terms up to DOID_4 / HP_0000118,
#           minimal intermediates), not STAR over 28 MB of doid.owl and hp.obo.
#           WONT bridges to them with skos:relatedMatch only, so no logical
#           seam runs through them. The two axioms that ground HP under BFO
#           (HP_0000118 ⊑ UPHENO_0001001 ⊑ PATO_0000001) are carried over
#           explicitly from the previous module set.
#     Result: obi_module 0.9 MB, 248 classes, one root (`entity`); the DOID
#     island is the 19 referenced terms plus their path to `disease`.
#     go/chebi/dron leaf modules are NOT rebuilt unless --leaf-modules is
#     given: go_module.owl carries hand-added property labels (commit 3a3859d)
#     that a rebuild from go_import.owl would silently drop.
#     2026-10-08: it also carries 43 GO classes the WONT addition reuses
#     instead of minting twins (Cell Adhesion, Metabolism, ...; the list and
#     the reading of each is Wound ontology/data/review/go_twins_2026-10-08.json),
#     MIREOT-extracted from Import ontologies/go.owl with all intermediates and
#     merged in, plus the exact synonym "deoxyribonucleic acid replication" on
#     GO_0006260. A --leaf-modules rebuild must seed those 43 or they go back
#     to being WONT twins. Backup before the merge:
#     Wound ontology/data/backup/go_module_before_go_twins_2026-10-08.owl
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
#   bash build_disease_proposal.sh --leaf-modules  # also rebuild go/chebi/dron
#                                                  #   from src/ontology/imports
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
LEAF_MODULES=false
for arg in "$@"; do
  case "$arg" in
    --no-reason)   RUN_REASON=false ;;
    --stubs)       RUN_STUBS=true ;;
    --full-giants) FULL_GIANTS=true ;;
    --leaf-modules) LEAF_MODULES=true ;;
  esac
done
 
# Sources that go through STAR and are merged for the JOINT extraction (FIX 1).
# Order doesn't matter; robot merge dedupes.
# FIX 3: pato.owl is NOT merged whole -- its own STAR module is (see step 3a2);
# uo/doid/hp are handled separately (label stub / MIREOT paths).
STAR_SOURCES=(
  bfo:"$IMP/bfo-core2020.owl"
  ro:"$IMP/ro.owl"
  iao:"$IMP/iao.owl"
  obi:"$IMP/obi.owl"
  ogms:"$IMP/ogms.owl"
  cob:"$IMP/cob.owl"
)
# Namespace buckets whose seed terms feed the joint STAR extraction.
STAR_BUCKETS=(bfo ro iao obi ogms cob pato upheno)   # upheno: obi.owl states UPHENO_0001001 ⊑ PATO_0000001
 
# ── Step 1: Build a base TTL that only imports ground_truth ────────────────────
echo "[1/5] Creating base (disease proposal with only ground_truth import)..."
python3 - "$INPUT" "$TMP/base.ttl" << 'PYEOF'
import sys, re
with open(sys.argv[1]) as f:
    content = f.read()
# The import list may end in ';' (more header annotations follow) or '.';
# keep whichever terminator the file uses.
content, n = re.subn(
    r'owl:imports\s+<[^>]+>(?:\s*,\s*<[^>]+>)*\s*([;.])',
    r'owl:imports <https://bioportal.bioontology.org/ontologies/WONT> \1',
    content, flags=re.DOTALL,
)
if n != 1:
    sys.exit(f"  ERROR: expected exactly one owl:imports list in {sys.argv[1]}, found {n}")
with open(sys.argv[2], 'w') as f:
    f.write(content)
print("  Base TTL written (import list replaced).")
PYEOF
 
# WONT imports MILD back; point that IRI at the rewritten base so the closure
# is exactly {WONT, MILD-own-content} and never the module files.
cat > "$TMP/catalog-v001.xml" << CATEOF
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<catalog prefer="public" xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog">
    <uri id="Imports Wizard Entry" name="https://bioportal.bioontology.org/ontologies/WONT"
         uri="file:/Users/Strubbelig/Library/Mobile%20Documents/com~apple~CloudDocs/Forschung/Ontology/Wound%20ontology/data/ground%20truth/ground_truth_final.owl"/>
    <uri id="MILD base" name="https://bioportal.bioontology.org/ontologies/MILD"
         uri="file:$TMP/base.ttl"/>
</catalog>
CATEOF

# A curated file must not import a full source ontology directly: the seed
# would then be the whole of that ontology. Refuse rather than build junk.
if grep -q -E '<http://purl.obolibrary.org/obo/[a-z]+/(releases/)?[0-9]{4}-[0-9]{2}-[0-9]{2}/[a-z]+\.owl>' \
     "$TMP/base.ttl" "/Users/Strubbelig/Library/Mobile Documents/com~apple~CloudDocs/Forschung/Ontology/Wound ontology/data/ground truth/ground_truth_final.owl"; then
  echo "ERROR: WONT or MILD imports a full OBO release directly. Remove that import;"
  echo "       the term reaches the closure through the module built here." >&2
  exit 1
fi
 
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
    'hp','chebi','doid','dron','ncbi','uo','upheno','uberon','fma')}
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
        # no uberon source locally; pato.owl bundles the few UBERON terms in use
        elif local.startswith('UBERON_'):                buckets['uberon'].append(iri)
        elif local.startswith('FMA_'):                   buckets['fma'].append(iri)
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
echo "[3/5] Joint STAR extraction (merged bfo+ro+iao+obi+ogms+cob + PATO-STAR; uo stub; doid/hp MIREOT)..."
 
# 3a. Build the combined seed (union of the six STAR buckets).
: > "$TMP/seed_core.txt"
for b in "${STAR_BUCKETS[@]}"; do
  [[ -s "$TMP/termfile_${b}.txt" ]] && cat "$TMP/termfile_${b}.txt" >> "$TMP/seed_core.txt"
done
# FIX 4 (2026-10-03): ALL of BFO core is seeded, not only the BFO terms WONT/MILD
# happen to name. BFO is the top ontology: WONT, MILD and the modules become the
# extraction schema and the class hierarchy, so every BFO class must be there
# with BFO's own subsumption. Seeded by use only, the closure held 20 of the 36
# classes and 19 of the 35 edges (no object, site, fiat object part, history,
# relational quality ...). Curator: "every bfo class should be in there and
# with correct hierarchy".
BFO_CORE="$IMP/bfo-core2020.owl"
n_bfo=$(grep -o 'owl:Class rdf:about="http://purl.obolibrary.org/obo/BFO_[0-9]*"' "$BFO_CORE" \
  | sed 's/.*rdf:about="//; s/"$//' | sort -u | tee -a "$TMP/seed_core.txt" | wc -l | tr -d ' ')
if [[ "$n_bfo" -lt 36 ]]; then
  echo "ERROR: expected 36 BFO core classes in $BFO_CORE, found $n_bfo" >&2; exit 1
fi
echo "  BFO core seeded whole: $n_bfo classes"
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
 
# 3a2. FIX 3(a): PATO on its own first, then its module joins the merge.
# The two roots of the ChEBI leaf module are grounded under BFO only by the
# copies pato.owl bundles (CHEBI_24431 ⊑ BFO_0000040, CHEBI_50906 ⊑
# PATO_0000001); seed them here so the leaf module does not dangle.
if [[ -s "$TMP/termfile_pato.txt" ]]; then
  printf 'http://purl.obolibrary.org/obo/CHEBI_24431\nhttp://purl.obolibrary.org/obo/CHEBI_50906\n' \
    | tee -a "$TMP/termfile_pato.txt" >> "$TMP/seed_core.txt"
  # BOT, not STAR: BOT keeps every superclass link (STAR alone would drop
  # `CHEBI_24431 ⊑ BFO_0000040` because BFO_0000040 is not a PATO seed); the
  # joint STAR below then trims against the full seed, where it IS present.
  $ROBOT extract --method BOT --input "$IMP/pato.owl" \
    --term-file "$TMP/termfile_pato.txt" \
    --output "$TMP/pato_star.owl" 2>/dev/null
  echo "  pato_star (PATO alone, BOT): $(wc -l < "$TMP/pato_star.owl" | tr -d ' ') lines"
  core_merge_args+=(--input "$TMP/pato_star.owl")
  $ROBOT merge "${core_merge_args[@]}" --output "$TMP/sources_core.owl" 2>/dev/null
  echo "  merged STAR sources + pato_star: $(wc -l < "$TMP/sources_core.owl" | tr -d ' ') lines"
fi

# 3c. Single STAR extraction over the merged sources + combined seed.
$ROBOT extract --method STAR --input "$TMP/sources_core.owl" \
  --term-file "$TMP/seed_core.txt" \
  --output "$TMP/extract_core.owl" 2>/dev/null
echo "  extract_core: $(wc -l < "$TMP/extract_core.owl" | tr -d ' ') lines"
core_bytes=$(wc -c < "$TMP/extract_core.owl" | tr -d ' ')
if (( core_bytes > 3000000 )); then
  echo "ERROR: extract_core is ${core_bytes} bytes; the joint STAR module ran away again" >&2
  echo "       (0.9 MB expected). A full source ontology is back in the merge or the seed." >&2
  exit 1
fi

# 3d. FIX 3(c): DOID and HP as MIREOT paths from the seed terms to their root.
if [[ -s "$TMP/termfile_doid.txt" ]]; then
  $ROBOT extract --method MIREOT --input "$IMP/doid.owl" \
    --lower-terms "$TMP/termfile_doid.txt" \
    --upper-term "http://purl.obolibrary.org/obo/DOID_4" \
    --intermediates minimal --output "$TMP/extract_doid.owl" 2>/dev/null
  echo "  extract_doid (MIREOT): $(wc -l < "$TMP/extract_doid.owl" | tr -d ' ') lines"
fi
if [[ -s "$TMP/termfile_hp.txt" ]]; then
  $ROBOT extract --method MIREOT --input "$IMP/hp.obo" \
    --lower-terms "$TMP/termfile_hp.txt" \
    --upper-term "http://purl.obolibrary.org/obo/HP_0000118" \
    --intermediates minimal --output "$TMP/extract_hp_path.owl" 2>/dev/null
  # HP_0000118 ⊑ UPHENO_0001001 is what the sources say, with one intermediate
  # left out: hp.owl (2026-06-06) asserts HP_0000118 ⊑ UPHENO_0001003 and
  # upheno.owl (2025-10-12) asserts UPHENO_0001003 ⊑ UPHENO_0001001. The local
  # hp.obo carries neither, so the collapsed path is written here rather than
  # extracted. Nothing is invented: both halves are quoted from their owners.
  # (UPHENO_0001001 ⊑ PATO_0000001 comes through the joint STAR from obi.owl.)
  cat > "$TMP/hp_ground.owl" << 'OWLEOF'
<?xml version="1.0"?>
<rdf:RDF xmlns:obo="http://purl.obolibrary.org/obo/"
     xmlns:owl="http://www.w3.org/2002/07/owl#"
     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
     xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">
    <owl:Ontology rdf:about="http://purl.obolibrary.org/obo/wond/modules/hp_ground_tmp.owl"/>
    <owl:Class rdf:about="http://purl.obolibrary.org/obo/HP_0000118">
        <rdfs:subClassOf rdf:resource="http://purl.obolibrary.org/obo/UPHENO_0001001"/>
        <rdfs:comment xml:lang="en">Collapsed from hp.owl (HP_0000118 subClassOf UPHENO_0001003) and upheno.owl (UPHENO_0001003 subClassOf UPHENO_0001001); the local hp.obo omits both. Stated by the owners, not by this build.</rdfs:comment>
    </owl:Class>
    <owl:Class rdf:about="http://purl.obolibrary.org/obo/UPHENO_0001001"/>
</rdf:RDF>
OWLEOF
  $ROBOT merge --input "$TMP/extract_hp_path.owl" --input "$TMP/hp_ground.owl" \
    --output "$TMP/extract_hp.owl" 2>/dev/null
  echo "  extract_hp (MIREOT + grounding): $(wc -l < "$TMP/extract_hp.owl" | tr -d ' ') lines"
fi

# 3e2. UBERON: no local source; pato.owl bundles the terms in use (one:
# UBERON_0000344 mucosa). A BOT/STAR seed there drags 145 GO and 47 UBERON
# classes plus two new roots in (measured), so take the MIREOT path straight
# to BFO_0000040 instead. Goes into obi_module beside the joint extract.
if [[ -s "$TMP/termfile_uberon.txt" ]]; then
  $ROBOT extract --method MIREOT --input "$IMP/pato.owl" \
    --lower-terms "$TMP/termfile_uberon.txt" \
    --upper-term "http://purl.obolibrary.org/obo/BFO_0000040" \
    --intermediates minimal --output "$TMP/extract_uberon.owl" 2>/dev/null
  echo "  extract_uberon (MIREOT to material entity): $(wc -l < "$TMP/extract_uberon.owl" | tr -d ' ') lines"
fi

# 3e3. FMA: the superclass path of every FMA term in use (Skin, Anatomical
# structure), MIREOT from the OBO-IRI edition of FMA up to `Anatomical
# entity`. FMA does not import BFO, so `Anatomical entity` is a root beside
# `entity` in the closure. That is accepted, not patched: we author axioms
# about our own classes only, never about a class another ontology owns
# (decided 2026-09-17; the two grounding axioms that used to be added here
# were removed for that reason, and the MILD header says so).
if [[ -s "$TMP/termfile_fma.txt" ]]; then
  $ROBOT extract --method MIREOT --input "$IMP/fma_obo.owl" \
    --lower-terms "$TMP/termfile_fma.txt" \
    --upper-term "http://purl.obolibrary.org/obo/FMA_62955" \
    --intermediates all --output "$TMP/extract_fma.owl" 2>/dev/null
  echo "  extract_fma (MIREOT): $(wc -l < "$TMP/extract_fma.owl" | tr -d ' ') lines"
fi

# 3e. FIX 3(b): UO is the one term in use, as a label stub.
if [[ -s "$TMP/termfile_uo.txt" ]]; then
  $ROBOT filter --input "$IMP/uo.owl" --term-file "$TMP/termfile_uo.txt" \
    --select "self annotations" --output "$TMP/extract_uo.owl" 2>/dev/null
  echo "  extract_uo (label stub): $(wc -l < "$TMP/extract_uo.owl" | tr -d ' ') lines"
fi
 
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
  "$TMP/extract_core.owl" \
  "$TMP/extract_uberon.owl"
 
# ogms/cob/pato: label-carriers; all logic is in extract_core.
make_label_module ogms
make_label_module cob
make_label_module pato
# FIX 3: uo is a stub, doid/hp are MIREOT paths (their logic is NOT in obi_module).
make_module uo   "$TMP/extract_uo.owl"
make_module doid "$TMP/extract_doid.owl"
make_module hp   "$TMP/extract_hp.owl"

make_module upheno    "$TMP/extract_upheno.owl"
make_module fma       "$TMP/extract_fma.owl"
make_module ncbitaxon "$TMP/extract_ncbi.owl"
if $LEAF_MODULES; then
  for ns in go chebi dron; do
    make_module "$ns" "$IMP_WOND/${ns}_import.owl"
  done
else
  echo "  [kept] go/chebi/dron modules untouched (pass --leaf-modules to rebuild)"
fi
 
echo "Modules written to: $MODULE_DIR/"
 
# ── Merge disease proposal (modular artifact) ──────────────────────────────────
echo ""
echo "Merging disease proposal with modules..."
$ROBOT merge --input "$INPUT" --output "$OUTPUT" 2>&1 | grep -v "^$\|INFO" || true
echo "Merged → $OUTPUT ($(wc -l < "$OUTPUT" | tr -d ' ') lines, $(du -sh "$OUTPUT" | cut -f1))"
 
# ── Step 4b: every external class the curated files use must be labelled ───────
# (INSTRUCTIONS rule 34: a module carries everything the curated files
# reference, with a label. An unlabelled term is a term the modules lost.)
echo ""
echo "[4b] Checking that every external class WONT/MILD use is labelled in the closure..."
$ROBOT merge --input "$TMP/combined_own.owl" --input "$OUTPUT" \
  --output "$TMP/closure_check.owl" 2>/dev/null
cat > "$TMP/unlabelled.sparql" << 'SPARQLEOF'
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?t WHERE {
  { ?t a owl:Class } UNION { ?s rdfs:subClassOf ?t } UNION { ?r owl:someValuesFrom ?t }
  FILTER(isIRI(?t))
  FILTER NOT EXISTS { ?t rdfs:label ?l }
}
SPARQLEOF
$ROBOT query --input "$TMP/closure_check.owl" \
  --query "$TMP/unlabelled.sparql" "$TMP/unlabelled.csv" 2>/dev/null
# intersect with the external terms the curated files actually use
tail -n +2 "$TMP/unlabelled.csv" | tr -d '"' | sort -u > "$TMP/unlabelled.txt"
tail -n +2 "$TMP/external_terms.csv" | tr -d '"' | grep 'purl.obolibrary.org/obo/' \
  | grep -v '/obo/wond/' | sort -u > "$TMP/external_classes.txt"
missing=$(comm -12 "$TMP/unlabelled.txt" "$TMP/external_classes.txt" || true)
if [[ -n "$missing" ]]; then
  echo "ERROR: these external terms are used by WONT/MILD but have no label in the closure:" >&2
  echo "$missing" | sed 's/^/    /' >&2
  echo "       Seed them (a bucket in step 2, or the MIREOT paths in step 3) and rebuild." >&2
  exit 1
fi
echo "  all $(wc -l < "$TMP/external_classes.txt" | tr -d ' ') external terms in use are labelled."

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