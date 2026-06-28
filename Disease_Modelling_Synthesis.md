# Modelling Disease: A Synthesis to Inform Your Ontology

*Synthesised from the 41 full texts in "Disease onto papers". Goal: the findings and reasoning that bear on **how to model disease** between top-level and domain, with every critique of a current modelling approach flagged ⚠.*

---

## 1. The decision you are actually making

Every paper, formal or philosophical, is forced into a position on three coupled questions. Your ontology needs an explicit answer to each.

1. **Ontological category.** Is a disease a *continuant* (a state/disposition that the organism bears) or an *occurrent* (a process/causal chain that unfolds)? — Grenon & Smith's SNAP/SPAN split makes this a forced choice in BFO; Mizoguchi denies the choice is clean.
2. **Grounding of "abnormal/pathological".** What makes the bearer pathological — statistical sub-normal function (Boorse), evolutionary dysfunction (Wakefield/Schwartz), harm/disvalue (normativists), or a primitive medical "pathologicity" (Hucklenbroich)? Every formal ontology *imports* this from philosophy of medicine and almost none of them say which.
3. **Crisp vs graded.** Are disease classes crisp universals with necessary-and-sufficient conditions, or inherently vague/prototype-based (Sadegh-Zadeh)?

The literature does not converge. What it gives you is a map of the trade-offs and a long list of failure modes to avoid.

---

## 2. The formal-ontology approaches (and their critiques)

### 2a. OGMS / BFO — *disease = disposition*
**(Scheuermann, Ceusters & Smith 2009; Goldfain et al. 2010; Arp/Smith/Spear 2015)**

The canonical realist model, four linked primitives:

- **Disorder** = a causally relatively isolated, **clinically abnormal**, *maximal* combination of physical components (the tumour, the mutated DNA). The material *physical basis*.
- **Disease** = a **disposition** (i) to undergo pathological processes that (ii) exists because of one or more disorders.
- **Pathological process** = a bodily process that is the *manifestation* of a disorder.
- **Disease course** = the totality of processes realising a disease instance.

Why they do it this way: a disposition can exist *before* it manifests (pre-clinical disease), lets one patient bear a disease *and* a predisposition to another, and absorbs inter-patient variation into the *course* rather than the disease itself.

> ⚠ **Critiques of the disposition model**
> - **Röhl & Jansen (2014):** the realizable taxonomy is incoherent where it matters most. If disease/function are *dispositions*, you **cannot represent malfunction** — malfunction is precisely *having a function but lacking the matching disposition*. They argue Function and Disposition must be **disjoint siblings** under Realizable, not parent/child (contra BFO 2's plan to subsume Function under Disposition). Directly undercuts the "disease as a kind of dysfunction-disposition" move.
> - **Jansen (2007):** medical reality is full of **graded** realizables ("suicidal tendency", "thrombophilic tendency") that a single crisp `Disposition` class represents badly; ontologies need *tendencies* (counteractable, probabilistic, partially-manifesting) as first-class citizens. A binary has-disposition/lacks-disposition model loses this.
> - **Rovetto & Mizoguchi (2015):** locating the disease in a *disposition* hides the **causal structure** that clinicians actually reason with; the disorder→process→disorder chain is the explanatory object, not a single dispositional property.
> - **Schulz et al. (2009)** (see §4): the disposition definition is *de re* and universally quantified, but most clinical "disease knowledge" is *default/probabilistic* — forcing it into BFO-style universal axioms misrepresents it.
> - **Hucklenbroich (2014):** the disposition framing is parasitic on an undefined notion of "**pathological**"; OGMS leaves *pathologicity* primitive, so the hard problem is untouched, only relocated.

### 2b. Mizoguchi River Flow Model / YAMATO — *disease = causal chain*
**(Rovetto & Mizoguchi 2015; Yamagata et al. 2013, 2014; Mizoguchi & Borgo 2022)**

Disease = a **dependent entity constituted of causal chains of clinical disorders** — sequences of causally-linked pathological processes/states directed toward pathology. 6,000 diseases / 17,000+ causal relations implemented.

Key conceptual moves you can borrow:
- **Object/process interdependence** (Galton & Mizoguchi): an object is "the interface between internal and external processes"; neither continuant nor occurrent is prior. This *dissolves* the SNAP/SPAN forced choice rather than answering it.
- The **river analogy**: a disease, *like a river*, is categorised as a **continuant** that nonetheless *persists through* constant processual change and is *characterised by* its flow. So RFM is **not** simply "disease is a process" — it is "disease is a persisting entity individuated by a causal-process structure." (Worth getting this nuance right; it is widely misreported.)
- **Abnormal state = Property = Attribute + Value** (Yamagata 2014): a three-layer ontology (generic → disease-specific) representing each abnormal state qualitatively so that **quantitative lab values link to qualitative disease concepts**. This is the most directly *implementable* idea in the corpus.

> ⚠ **Critiques / tensions in the causal-chain model**
> - **Self-admitted (Rovetto & Mizoguchi 2015):** there is *no philosophical agreement on the relata of causation* (events? processes? facts?) and no agreement on what unifies the parts of a causal chain into one mind-independent whole — so the chain's identity conditions are under-determined.
> - Causal chains have **vague spatio-temporal boundaries** ("crisp boundaries are rare in biology") — pushes you toward the fuzziness problem (§3e).
> - Built on **YAMATO, not BFO** (Mizoguchi & Borgo 2022 position YAMATO as a rival top-level with richer treatment of quality/representation/process). Adopting RFM wholesale means a top-level commitment that is *not* OBO-mainstream — an interoperability cost.

### 2c. DOID and Mondo — *pragmatic classification*
**(Schriml et al. 2012/2015/2019/2022; Kibbe et al. 2015; Vasilevsky et al. 2022)**

DOID and Mondo are **classification/integration** resources, not metaphysical theories. Mondo's root class literally imports the **OGMS disposition definition**, but its *working* identity criterion for a **disease entity** (leaf node only) is clinical and four-fold: **(1) etiology, (2) phenotypic feature(s), (3) characteristic natural history/time course, (4) [optionally] typical treatment response**.

> ⚠ **Critiques / limitations**
> - Mondo concedes that harmonised classification **"may, by design, partially disagree with any particular source"** and deliberately uses `skos:exactMatch` instead of `owl:equivalentClass` because forcing OWL coherence across sources *"is not guaranteed to produce a coherent result."* I.e. they **trade logical rigour for coverage** — the opposite of what a between-top-and-domain ontology should do.
> - The disposition root and the clinical four-feature criterion are **never reconciled**; the metaphysics is decorative. This is exactly the gap your project can fill.
> - DOID's historically *single-inheritance, location/etiology-mixed* axes conflate orthogonal dimensions (anatomy vs cause vs phenotype).

### 2d. Substrate: bodily systems and function
**(Smith, Munn & Papakin 2004)** — disorders are predicated of **bodily systems** individuated *functionally and spatially*, not just anatomically. Whatever you choose, you need a principled account of the *bearer* (system/structure) before you can say it is disordered.

---

## 3. What philosophy of medicine tells you about "pathological" (and why no off-the-shelf answer is safe)

Your formal model has to bottom out in one of these, so know their failure modes.

### 3a. Naturalism — Boorse's Biostatistical Theory (BST)
**(Boorse 1977, 1997, 2014)** Disease = an internal state reducing one or more **functional abilities below the statistically typical level** for the organism's **reference class** (age × sex × species). Value-free, the default "scientific" definition and the implicit grounding of OGMS "clinically abnormal".

> ⚠ **Critiques**
> - **Kingma (2010):** functions must be **indexed to a situation** (the heart's "normal" output differs at rest vs exercise). But once you index to situations, the BST **can no longer distinguish health from disease** — pathological responses occur in *their* characteristic situations too (poison, polio). The **reference-class choice is doing illicit normative work**.
> - **Schwartz (2007):** "dysfunction" needs a *line* between normal and abnormal that neither pure statistics nor selected-effect function can draw non-arbitrarily.
> - **Hausman (2012):** rescue naturalism only by abandoning the sharp line for **graded functional efficiency** — which concedes the crisp-universal model.

### 3b. Normativism / hybrids
**Engelhardt (1975):** disease judgements are ineliminably **value-laden**. **Wakefield's** Harmful Dysfunction (factual dysfunction + harm) is the dominant hybrid. **Cooper** (via Smart 2016): disease = a condition that is *(i) bad to have, (ii) treatable, (iii) one we'd be unlucky to have*.
> ⚠ Normativism imports values you may not want in a reference ontology; hybrids inherit *both* the dysfunction problem (§3a) *and* the indeterminacy of "harm".

### 3c. The "disease entity" tradition — Hucklenbroich
**(Hucklenbroich 1984, 2014)** Treats **disease entity** as the *primitive* theoretical concept of medicine (like "mass" in physics), grounded in **pathologicity** criteria (e.g. threats to life, pain/suffering, loss of ability/fertility) rather than statistics or values. Diseases are clinical **natural kinds** (a nosology).
> Useful because it *legitimises taking disease/pathologicity as a defined-by-criteria primitive* rather than reducing it to function — a middle path between Boorse and normativism, and friendlier to a mid-level ontology than either.

### 3d. Causal/mechanistic accounts
**Smart (2016)** proposes **causal/multifactorial classification of disease** for clinical medicine. **Tsou (2016)** argues disease kinds are natural kinds *in virtue of shared causal mechanisms* (mechanistic property clusters). Both align with the Mizoguchi causal-chain intuition and give you a principled basis for *grouping* diseases.

### 3e. Vagueness — the problem every crisp ontology ignores
**Sadegh-Zadeh (2000):** health, illness, disease are **fuzzy sets** with graded membership; replace Aristotelian crisp categories with a **prototype-resemblance** theory. Echoed by Rovetto & Mizoguchi's "crisp boundaries are rare in biology".
> ⚠ A pure OWL/DL ontology with necessary-and-sufficient class definitions **structurally cannot represent** graded disease membership. Decide early whether you accept this limitation, push gradedness into data/annotations, or adopt fuzzy/values-based machinery.

### 3f. Deflationists / eliminativists — do you even need the class?
**Hesslow (1993):** clinical decisions turn on **specific facts** (prognosis, treatability, consequences), not on whether the health/disease line is crossed; the concept of disease is "superfluous" for decision-making. **Worrall & Worrall (2001):** the definitional project is "much ado about nothing". **Lemoine (2013):** conceptual analysis *cannot* decide naturalism vs normativism (stipulation + counterexamples let everyone "win"); the concept should be **naturalised empirically** instead.
> Takeaway for you: don't try to win the definition by analysis. **Pick a stipulated, fit-for-purpose definition, state the purpose, and justify by utility** — exactly what OGMS *says* it does but doesn't follow through on.

---

## 4. Cross-cutting critiques that apply to *any* formal model

These are the ones most likely to bite your implementation, independent of which camp you join.

- ⚠ **Don't conflate ontology with probabilistic knowledge (Schulz et al. 2009).** They distinguish four representation types (lexico-semantic, universal/type-level, instance-level, default/probabilistic) and argue that **standard or statistical clinical knowledge cannot be expressed as universally-quantified ontological axioms** without falsehood ("every diabetic has…" is false). Keep the *ontology* (necessary, all-instances) separate from *clinical default knowledge* (most instances). Most disease "definitions" are actually the latter.
- ⚠ **Primitives are unavoidable (Scheuermann et al. 2009).** Some terms must stay undefined to avoid regress; "abnormal/pathological" is the load-bearing primitive in every model. Be explicit about *which* terms you leave primitive and *why*, rather than hiding the choice.
- ⚠ **Realism is a contested commitment (Schulz et al. 2009; Mizoguchi & Borgo 2022).** BFO-style "ontological realism" is not neutral; a competing top-level (YAMATO/DOLCE) changes what disease *can* be. Your between-top-and-domain layer inherits whatever you put above it — choose the top-level deliberately.
- ⚠ **Universals vs defaults vs reference classes interact.** Boorse's reference-class relativity (§3a) means even "abnormal" is *class-indexed*; an ontology that asserts disease universals without reference-class parameters smuggles in a hidden population.

---

## 5. Concrete recommendations for your design

A defensible synthesis, given the above:

1. **Separate four layers explicitly** (this is the single highest-value move, and where DOID/Mondo are weakest): **bearer** (bodily structure/system) → **disorder** (the abnormal material basis) → **causal-process structure** (the chain of pathological processes/states) → **disease** (the persisting entity individuated by that structure). OGMS and RFM each give you some of these; neither cleanly gives all four.
2. **Treat the disease as a persisting (continuant) entity *individuated by* its causal-process structure** — the RFM "river" reading. This keeps pre-clinical existence (OGMS's main motivation) *and* the causal explanatory content (RFM's), without committing you to "disease = a single disposition" (which Röhl & Jansen show breaks on malfunction).
3. **Adopt a richer realizable layer than BFO's** if you stay disposition-adjacent: keep **Function and Disposition disjoint** (Röhl & Jansen) and add **Tendency** as a graded realizable (Jansen 2007) so risk/predisposition and partial manifestation are representable.
4. **Make "pathologicity" a named, criteria-defined primitive** (Hucklenbroich) rather than silently importing Boorse. State the criteria; don't pretend it's value-free statistics if it isn't.
5. **Decide your stance on vagueness up front** (Sadegh-Zadeh). Recommended for an OWL ontology: keep crisp *classes*, push graded membership and thresholds into **annotation/quantitative data** (Yamagata's attribute–value layer is the mechanism), and document that the crispness is a representational convenience, not a metaphysical claim.
6. **Keep the ontology (all-instances, necessary) strictly separate from clinical default knowledge** (Schulz). Diseases' "typical features" belong in a defaults/association layer, not in class equivalence axioms.
7. **Justify by purpose, not by analysis** (Lemoine, Hesslow). State the use cases your disease model must serve and evaluate competing definitions by fit — the conceptual-analysis war is unwinnable.

**The gap you can claim:** no existing resource reconciles a *causal-structural* individuation of disease (RFM/Smart/Tsou) with a *clean realizable ontology* (Röhl & Jansen) and an *honest, criteria-based pathologicity primitive* (Hucklenbroich), kept *separate from default clinical knowledge* (Schulz). That combination is your contribution.
