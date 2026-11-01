"""Moritz 2026-10-31: re-read the pathology grounding strictly ("2 streng, vage als offen") and drop the two
score-3 classes to 2 ("1 ja": the score-3 rule is not justified for EFO disease and CPRO pathological disposition).

A class counts as explicit only when its definition says what makes a condition pathological. Circular
definitions ("pathological processes", "disorders", a list of signs and symptoms), MeSH/OGMS copies, a mere
example, no definition, and vague ones ("improper/abnormal function" without a standard) become `undefined`.
Kept explicit (7): BioTop, POEM, NCI-based BERO and CANCO (harm: discomfort, dysfunction or distress) =
normative; SL_DIS (dysfunction that causes distress) = harmful dysfunction (evolutionary_function code);
ExO and NIFSTD OGMS_0000031 (comparison with other members of the species, DOID_4 text) = statistical."""
import pandas as pd
F = "Extraction Tables/disease_terms_review_enriched.csv"
d = pd.read_csv(F, dtype=str, keep_default_na=False)
inc = d.effective_synthesis_status == "include"
EXPLICIT = {
    "http://purl.org/biotop/biotop.owl#PathologicalDisposition": "normative",
    "http://purl.org/twc/poem/Disorder": "normative",
    "http://purl.obolibrary.org/obo/NCIT_C2991": "normative",
    "http://chem.deri.ie/granatum#Disease": "normative",
    "http://example.org/ontology/Disorder": "evolutionary_function",
    "http://purl.obolibrary.org/obo/ExO_0000079": "statistical",
    "http://purl.obolibrary.org/obo/OGMS_0000031": "statistical",
}
SCORE2 = {"http://purl.obolibrary.org/obo/MONDO_0000001", "http://purl.org/cpr/pathological-disposition"}
NOTE_G = "[2026-10-31] pathology grounding re-read strictly: the definition does not state what makes a condition pathological (circular, copied, vague or absent) -> undefined."
NOTE_S = "[2026-10-31] entity quality score 3 -> 2: pathology not grounded (circular OGMS wording) and silent on crisp vs graded."
n_g = n_s = 0
for i in d.index[inc]:
    iri, g = d.at[i, "class_iri"], d.at[i, "pathological_grounding"]
    if g in ("undefined", "not_applicable"):
        continue
    new = EXPLICIT.get(iri, "undefined")
    assert sum(d.loc[inc, "class_iri"] == iri) == 1, iri
    if new != g:
        d.at[i, "pathological_grounding"] = new
        if new == "undefined":
            d.at[i, "review_comment"] = (d.at[i, "review_comment"] + " | " if d.at[i, "review_comment"] else "") + NOTE_G
        n_g += 1
for i in d.index[inc & d.class_iri.isin(SCORE2)]:
    assert d.at[i, "entity_quality_score"] in ("3", "3.0"), d.at[i, "entity_quality_score"]
    d.at[i, "entity_quality_score"] = "2"
    d.at[i, "review_comment"] = (d.at[i, "review_comment"] + " | " if d.at[i, "review_comment"] else "") + NOTE_S
    n_s += 1
assert n_s == 2
d.to_csv(F, index=False)
print("grounding changed", n_g, "scores changed", n_s)
