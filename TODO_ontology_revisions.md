# TODO — Disease ontology revisions (Protégé)

Work items to align `Disease proposal 2.ttl` with the modelling stance (realist material instances · epistemic categories · pathologicity primitive · persistence-through-change). Manchester strings are written for the **class-expression editor** with "render entities using rdfs:label" ON. Relation/class IRIs are given once for lookup.

**Relation labels ↔ IRIs**
`part of`=BFO_0000050 · `has part`=BFO_0000051 · `has realization`=BFO_0000054 · `realizes`=BFO_0000055 · `participates in`=BFO_0000056 · `has participant`=RO_0000057 · `inheres in`=RO_0000052 · `bearer of`=RO_0000053 · `has quality`=RO_0000086 · `has phenotype`=RO_0002200 · `has input`=RO_0002233 · `has output`=RO_0002234 · `output of`=RO_0002353 · `material basis of`=BFO_0000127 · `has material basis`=BFO_0000218 · `is about`=IAO_0000136 · `immediately causally downstream of`=RO_0002405
**Class labels ↔ IRIs**
`material entity`=BFO_0000040 · `phenotypic abnormality`=HP_0000118 · `absent`=PATO_0000462 · OGMS `disorder`=OGMS_0000045

---

## A. `material disease entity` (WOND_120020)

- [ ] **T1** Delete the annotation *"The set of pathological disorders in one individual"* (forces co-occurring diseases to merge). Replace gloss with:
  > A material entity that has one or more pathological disorders as parts; which disorders compose one disease is fixed by the diagnostic classification assigned to them, not by an intrinsic unity criterion.
- [ ] **T2** Set the necessary condition to just:
  ```
  material entity
   and ('has part' some 'pathological disorder')
  ```
  Do **not** assert any maximal/unity axiom. (Individuation handled in F.)
- [ ] **T3** Remove `('output of' some 'disease development process')` from WOND_120020. If you want the acquired case, create subclass `acquired material disease entity`:
  ```
  'material disease entity'
   and ('output of' some 'disease development process')
  ```
- [ ] **T4** Decide on `('participates in' some 'course of the disease process')`: keep as-is (defensible) **or** move to a subclass. Don't leave it unexamined.
- [ ] **T5** Add a `definition`/`comment` annotation recording the identity criterion:
  > Identity is grounded in the historical-causal continuity of the disorder lineage, not in momentary material composition (cf. a river persisting through complete material replacement).

## B. `pathological disorder` (WOND_120022) — make pathologicity primitive

- [ ] **T7** Choose the parent:
  - *Option 1 (independent):* create a new `disorder` root (new WOND id) `⊑ material entity`; put `pathological disorder` under it; link to OGMS via `oboInOwl:hasDbXref`/`skos:closeMatch` **instead of** `subClassOf`.
  - *Option 2 (anchored):* keep `pathological disorder ⊑ OGMS:disorder`.
- [ ] **T8** Keep it **primitive** (asserted superclasses only; no `equivalentClass`). Retain:
  ```
  'part of' some 'material disease entity'
  ```
  **Delete** the restriction `('has quality' some 'phenotypic abnormality')` (HPO terms aren't BFO qualities; the filler is vacuously generic anyway).
- [ ] **T8b** Add annotation property `pathologicity criteria` (or use `definition`) documenting the Hucklenbroich primitive (e.g. threat to life, pain/suffering, loss of ability/fertility) — pathologicity is asserted, not inferred.
- [ ] **T8c** *(optional)* If a biology-side phenotype link is wanted, attach to the **organism**, not the disorder:
  ```
  'Homo sapiens' and ('has phenotype' some <specific HP term>)
  ```

## C. Absence / privation disorders (e.g. monosomy X)

- [ ] **T9** Do **not** attach an `absent` quality. `'has quality' some 'absent'` predicates absence of the bearer ("the genome is absent" / "the pathology is absent"), which is meaningless — the thing absent is a *normal* component (the X chromosome), while the pathology is the resulting genome, which is fully present. A realist BFO ontology admits no negative entity or quality. Model the disorder as the **abnormally-constituted material bearer itself** — the karyotype / genome / cell that is abnormal because a normally-present part is missing. Pathologicity is asserted (primitive). Nothing else is required:
  ```
  'pathological disorder'          # the instance just IS e.g. the monosomic karyotype
  ```
  This is simply the *abnormal-organisation* case of your disorder definition; the absence need not be reified.
- [ ] **T9a** *(optional — only if the instance must record WHAT is missing)* use a **positive** relational count/configuration quality of the bearer, never "absent". E.g. a PATO relational number quality such as *"has fewer parts of type"* / *"decreased number"* directed **towards** the missing type:
  ```
  'pathological disorder'
   and ('has quality' some ('has fewer parts of type' that 'towards' some 'X chromosome'))
  ```
  (substitute the exact PATO term/IRI), or a cardinality on the bearer read under a normality/closure assumption, e.g. `('has part' exactly 1 'sex chromosome')`. If the claim depends on a norm, keep it in the knowledge layer.
- [ ] **T9b** Do **not** use OWL negation for absence (`not ('has part' some 'X chromosome')` / `complementOf`) inside class expressions — wrong semantics under the open-world assumption, and it wrecks the reasoner.
- [ ] **T10** Update the `disorder` definition text so absence folds into abnormal organisation: *a disorder is an abnormal presence or organisation of material components — including the limiting case where the abnormal organisation consists in a normally-present component being absent.* (No "absence quality"; the disorder-bearer is still a present, material entity.)

## D. Predisposition / risk (WOND_120023) — disentangle TWO senses

Clinical "predisposition" conflates two ontologically distinct things. Model them separately.

> **Convention (decided): the tendency always `inheres in` the organism (`Homo sapiens`); the grounding factor(s) — S_A disorder, variant, adiposity — attach via `has material basis`, never as the bearer.** Rationale: only the organism is a bearer in *all* cases (incl. no-disorder risk); risk is multifactorial and only the organism is the common locus; and it keeps "who is at risk" (organism) separate from "what grounds it" (material basis). The "diabetes predisposes to nephropathy" reading is recovered as `has material basis some <diabetes disorder>`, not as bearing.

- [ ] **T11 — Silent / subclinical disorder ("disorder without a phenotype").** This is **not** a predisposition: the pathological material is already present, it just has no observed phenotype yet (e.g. an early subclinical plaque). Because you removed phenotype from the disorder definition (T8), this is already just a `pathological disorder` instance with no observed phenotype — **no new class needed**. If you want to flag it, do so in the epistemic/observation layer (status "no phenotype observed yet"), not as a material kind. (This is a good argument *for* T8.)

- [ ] **T11a — Predisposition / risk proper ("potential with no disorder yet").** The obese patient with mint coronaries: there is *no disorder in the target organ at all*. Model as a **tendency** (Jansen 2007), not a plain disposition — risk is graded, counteractable (statins, weight loss) and only probabilistically realised, which is exactly the tendency profile. Bearer = the organism; it is realised in a *future* development process that produces the **target** disorder:
  ```
  'tendency'
   and ('inheres in' some 'Homo sapiens')
   and ('has realization' some
          ('disease development process'
            and ('has output' some 'pathological disorder')))   # narrow the filler to the target,
                                                                 # e.g. 'coronary pathological disorder'
  ```
  Ground it in the risk-conferring **present** material state via `('has material basis' some 'material entity')` (adiposity, genotype, or a variant — see T11d). The base **may** even be a pathological disorder (a pathogenic variant; or AIDS predisposing to opportunistic infection) — the only constraint is that the base is **distinct from** the *target* disorder it predisposes to (the `has output` filler). What does not yet exist is a disorder in the **target** organ (the mint coronaries).

- [ ] **T11b** Make the predisposition **disjoint** from both `pathological disorder` and `material disease entity` — it is neither a disorder nor a disease (OGMS: "a predisposition is a disposition to acquire a further disposition; not all predispositions are diseases"). Fix the description typo "tha bearer" → "the bearer".

- [ ] **T11c — Realizable hygiene (Röhl & Jansen 2014).** Keep `tendency`, `disposition`, `function` as distinct realizables; do not subsume `tendency` under `disposition`. If your BFO import lacks `tendency`, add it as your own subclass of `realizable entity` (annotate: graded, counteractable, partially-manifesting) rather than overloading `disposition`.

- [ ] **T11d — Risk borne by a present material entity (genetic variants).** Often the risk-bearer is a concrete present material entity — a pathogenic variant (BRCA1, Factor V Leiden), a portion of mutated DNA. Model the variant as a `material entity`; if you judge it pathological under your primitive criterion it is *also* a `pathological disorder` (an abnormal organisation of genetic material, typically phenotype-silent — T8/T11 cover that). The risk is a tendency it bears/grounds toward a future, distinct disorder:
  ```
  'tendency'
   and ('inheres in' some 'Homo sapiens')               # organism bears the risk (convention above)
   and ('has material basis' some 'genetic variant')    # the variant grounds it
   and ('has realization' some
          ('disease development process'
            and ('has output' some 'pathological disorder')))   # the future target disorder
  ```
  Whether the variant counts as a disorder is an independent primitive judgement, not forced by the model (OGMS: a disorder can itself be a predisposition to a further disorder).

- [ ] **T11e — Predisposition links disease A to disease B (your formalisation).** If disease A = the aggregate of disorder-set S_A and disease B = a *distinct* aggregate S_B, a predisposition is a **tendency** borne by the bearer of S_A (grounded in S_A, or in a variant/state) to **acquire S_B-type disorders** in the future; its realisation is a development process whose output disorders aggregate into a material disease entity of type B, which can then be the referent of a **disease-B diagnostic result**. Crucially, "the S_B set" is itself fixed by the B diagnostic category (epistemic individuation, T13), so the tendency is precisely *"tendency to acquire disorders that would be grouped under B."*
  ```
  'tendency'
   and ('inheres in' some ('Homo sapiens' and ('bearer of' some <S_A disorder>)))
   and ('has realization' some
          ('disease development process'
            and ('has output' some <S_B disorder>)))
  ```
  This is the **unrealised** face of the A→B link; your existing complication classes (`material complication disease entity` WOND_120051, `disease course process putting out disorders…` WOND_120053) are the **realised** face — the same process once it has fired. Align them: the predisposition's `has realization` filler should be the very complication/course process whose `has output` is the S_B disorder.

## E. Realist core vs epistemic categories

- [ ] **T12** Ensure **no** DOID class / named disease (Stevens-Johnson, Gustilo grades, etc.) is `subClassOf 'material disease entity'`. They attach only through the classification path.
- [ ] **T13** Break the individuation circularity (so diagnosis can group disorders). On `disease diagnostic result` (WOND_120024) change:
  - from `'is about' only 'material disease entity'`
  - to `'is about' some 'pathological disorder'`
  The disease is then the aggregate of exactly the disorders a given diagnostic result groups. No causal axiom needed.

## F. Unknown-substrate diseases (depression / migraine / epilepsy)

- [ ] **T14** Create the disease class, assert `⊑ 'material disease entity'` (commits existence), and put its *definition* (phenotype thresholds/criteria) in the epistemic layer via `disease threshold specification`. Annotate:
  > Material substrate asserted but not yet characterized; defined operationally at the classification layer.

## G. Technical fixes

- [ ] **T15** Typos: "patholgical" (120020), "ouput" (120092), "tha bearer" (120023).
- [ ] **T16** `compound pathological disorder` (WOND_120049): change `has part **only** 'pathological disorder'` → `has part **some** 'pathological disorder'` (the `only` form is vacuously true for partless individuals). Full intended definition:
  ```
  'pathological disorder'
   and ('has part' some 'pathological disorder')
  ```
- [ ] **T17** Run **ELK** (then **HermiT** for full DL) over the *merged* file with all imports. Confirm: ontology coherent; nothing unintended subsumes `material disease entity`; `material complication disease entity` and `disease course process putting out disorders…` remain satisfiable.

## H. Prose tensions to state in the paper (not axioms)

- [ ] **T18** Individuation is epistemic: only the **disorders** are fully mind-independent; the *bounded* disease is classification-relative. Soften "disease instances are mind-independent material entities" accordingly (see rewrite below).
- [ ] **T19** State that disorders are not uniformly positive material entities (absence case, T10).

---

## Rewrite — persistence section (replaces the final paragraph)

> Disease persistence is treated as continuant persistence through material change, not as identity of material constitution. A disease instance is a material entity that endures as one and the same continuant while its underlying biological material is continuously replaced — as a river remains the same river though its water does not. Its identity is grounded in the historical-causal continuity of the disorder lineage rather than in the particular matter present at any instant. Successive clinical observations therefore sample different material states of one persisting disease instance, not a succession of numerically distinct entities. What the diagnostic category tracks across time is this single, materially changing instance; the comparative stability of the category reflects the continuity of the underlying disorder lineage together with the persistence of the classification, while the material realization of the pathology turns over beneath it.

*(If you ever prefer the stage-based reading instead, disease would cease to be a BFO material continuant and you'd need a 4D/perdurantist re-base — incompatible with the current imports. The above keeps your material-replacement insight without that cost.)*
