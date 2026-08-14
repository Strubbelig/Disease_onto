# Independent Stratified Validation of Class Review

## Purpose

This procedure validates a manageable, deliberately heterogeneous sample of the completed class-level screening and charting. It does not replace the complete first review. The second reviewer should work independently before any disagreement discussion.

## Timing and sample size

Generate the sample only after all first-review eligibility decisions are complete and before the publication dataset is frozen. Review **50 unique class IRIs** (approximately 18% of the 276-record master table).

Use a fixed random seed and record it in the sample manifest. Sample without replacement from the final master CSV using these strata:

| Stratum | Target n | Sampling frame |
|---|---:|---|
| Included, `no_grounded_model` | 15 | Included classes with no identifiable disease model |
| Included, BFO disposition family | 10 | Disposition, realizable entity, or dependent continuant |
| Included, other or rare models | 10 | Process, state, BioTop condition, SIO quality, mixed, disorder, or unclear |
| Excluded, scope or resource type | 8 | Out-of-scope entity, thesaurus/value set, demo/training resource, or terminology-only exclusion |
| Excluded, duplication or reuse | 7 | Imported/mapping-only, exact-match, duplicate, replacement, or better-native-candidate exclusion |

If a stratum contains fewer records than its target, take all records in that stratum and redistribute the remainder proportionally across the other strata. The three reopened WebProtege-IRI records must receive their first-review decisions before sampling; they are not automatically forced into the validation sample.

## Material shown to the second reviewer

Provide a separate sample CSV and the same evidence packets used in the UI. Show the class IRI, ontology/source identifiers, labels, definitions, comments, synonyms, asserted named parents, mappings, provenance, and source citation where available.

Blind these first-review fields until independent extraction is complete:

- include/exclude decision and exclusion reason;
- review comment and publication decision note;
- disease-model and four coupled design-decision categories;
- evidence-quality ratings and score;
- citation-approval decision;
- reviewer identity and review date.

The second reviewer may inspect the underlying ontology artifact or cited publication when the evidence packet is insufficient and should record that consultation.

## Decisions to reproduce

For every sampled class, the second reviewer records:

1. include or exclude, with one controlled exclusion reason if excluded;
2. native, imported, or unclear provenance route;
3. disease-model category;
4. ontological category;
5. pathological grounding;
6. crisp-versus-graded category;
7. reality-versus-classification category;
8. definition, comment, and parentage quality;
9. overall entity-quality score;
10. a short rationale for any uncertain decision.

Citation assignment may be validated separately and should not be allowed to reveal the first reviewer's class-level coding.

## Reliability analysis

Preserve both reviewers' original values in separate columns. Report raw agreement for every controlled field. Report Cohen's kappa for eligibility and the major nominal categories when both reviewers use at least two categories in the sample. Report weighted kappa for the ordinal entity-quality score. Also report the number and percentage of exact agreements within each sampling stratum because kappa is sensitive to prevalence and the sample deliberately over-represents rare models.

Do not calculate kappa for a field on which both reviewers assign the same single category to every sampled class; report 100% agreement and explain that kappa is undefined in that case.

## Reconciliation

After the independent file is locked, compare decisions and flag every disagreement. Moritz Milewski and the second reviewer should reconcile disagreements by discussion using the recorded class evidence. Preserve the original values and record the adjudicated value plus a concise reason. If agreement cannot be reached, retain the class as unresolved and seek a third opinion before freezing the manuscript counts.

## Reporting

Report the sample size, fixed random seed, stratum counts, blinding procedure, fields reviewed, raw agreement, applicable kappa statistics, number of disagreements, and reconciliation method in Methods. State clearly that one reviewer completed the full dataset and a second reviewer independently validated a stratified sample.
