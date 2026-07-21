"""50 NL queries with ground-truth ontology sets for BioPortal-50 benchmark."""
from __future__ import annotations

# Each item: query text, list of ground-truth relevant ontology acronyms
QUERIES = [
    # Diabetes / treatment (SWRL+)
    ("How should metformin be adjusted for type 2 diabetes mellitus patients?", ["DMTO", "FASTO"]),
    ("Does this patient with diabetes have a contraindicated drug treatment plan?", ["DMTO", "FASTO"]),
    ("Guideline provenance for diabetes mellitus medication decisions", ["DMTO", "STATO"]),
    ("Insulin titration rules for hyperglycemia management", ["DMTO", "FASTO"]),
    ("Sensor-based monitoring of type 1 diabetes complications", ["FASTO", "DMTO"]),
    # Consent / information artifacts
    ("Does this research protocol need an informed consent form?", ["ICO", "IAO"]),
    ("Which information artifacts document patient consent signatures?", ["IAO", "ICO"]),
    ("Withdraw consent and related documentation obligations", ["ICO", "IAO"]),
    # Access control / situation
    ("Situation-based access control for clinical records", ["SITBAC", "IAO"]),
    ("May a nurse access emergency medical records in this situation?", ["SITBAC", "ICO"]),
    # MS / symptomatic treatment
    ("Symptomatic treatment options for multiple sclerosis fatigue", ["STMSO", "DOID"]),
    ("Are corticosteroids indicated for acute MS symptom flare?", ["STMSO", "DMTO"]),
    # Metabolism / bioprocess
    ("Interlocked metabolic processes regulating glucose uptake", ["BIPOM", "GO"]),
    ("Biological process ontology for cellular metabolism chains", ["BIPOM", "GO"]),
    # Agriculture / agro
    ("Pesticide exposure risk for crop plant traits", ["AGRO", "PO", "ENVO"]),
    ("Agronomic treatment ontology for irrigation and soil nutrients", ["AGRO", "ENVO"]),
    ("Plant phenotype under drought stress in agricultural systems", ["AGRO", "PO", "PATO"]),
    # Statistics / study design
    ("Statistical study design for observational clinical trials", ["STATO", "OBI"]),
    ("Which statistical assay variables are required for this analysis?", ["STATO", "OBI"]),
    # Social / roles
    ("Social roles of caregivers in clinical care pathways", ["OMRSE", "OGMS"]),
    ("Organization membership of a healthcare provider role", ["OMRSE", "OBI"]),
    # Disease / phenotype (reference)
    ("Human phenotype of progressive cerebellar ataxia", ["HP", "DOID", "MONDO"]),
    ("Disease ontology identifier for Alzheimer's disease", ["DOID", "MONDO", "ADO"]),
    ("Mouse phenotype abnormal blood glucose homeostasis", ["MP", "MA"]),
    ("Mondo classification of rare inherited metabolic disorders", ["MONDO", "DOID"]),
    # Chemicals / food
    ("Chemical entity classification of sodium benzoate preservative", ["CHEBI", "FOODON", "FOBI"]),
    ("Is sodium benzoate a food additive preservative compound?", ["CHEBI", "FOODON", "FOBI"]),
    ("Food ontology for dairy allergen ingredients", ["FOODON", "FOBI", "CHEBI"]),
    # Anatomy / cells
    ("Cell type ontology for pancreatic beta cells", ["CL", "MA"]),
    ("Mouse anatomical structure of the liver lobule", ["MA", "CL"]),
    ("Cell ontology relationship between neuron and glial cells", ["CL", "GO"]),
    # Environment / exposure
    ("Environmental exposure ontology for urban air pollution", ["ENVO", "OHMI"]),
    ("Habitat classification of freshwater wetland ecosystems", ["ENVO", "PO"]),
    # Gene / function
    ("Gene ontology annotation of apoptotic process", ["GO", "PR"]),
    ("Protein product of mitochondrial respiratory chain", ["PR", "GO"]),
    ("Sequence ontology for missense variant annotations", ["SO", "GO"]),
    # Hypertension / disease apps (SWRL- ADO/HTN in our set are without rules but topical)
    ("Hypertension diagnosis staging for adult patients", ["HTN", "DOID"]),
    ("Ontology terms for chronic hypertension management", ["HTN", "OGMS"]),
    # Units / measures
    ("Unit of measure for milligrams per deciliter blood glucose", ["UO", "PATO"]),
    ("Quality phenotype for elevated blood pressure measurement", ["PATO", "HTN"]),
    # Infection / pathology
    ("Infectious disease ontology of host-pathogen interactions", ["IDO", "OHMI"]),
    ("Ontology of host-microbe interactions in infection", ["OHMI", "IDO"]),
    # Chemistry methods
    ("Chemical methods ontology for chromatography assays", ["CHMO", "CHEBI"]),
    ("Bioassay ontology for kinase inhibition screens", ["BAO", "OBI"]),
    # Plants / development
    ("Plant ontology of leaf development stages", ["PO", "PATO"]),
    ("Zebrafish anatomy of the embryonic nervous system", ["ZFA", "GO"]),
    ("Xenopus anatomy of cardiac developmental structures", ["XAO", "GO"]),
    # Instruments / software
    ("Software ontology describing analysis workflow tools", ["SWO", "OBI"]),
    ("Ontology for medical device measurement fixing assays", ["FIX", "OBI"]),
    # Pregnancy / additive safety (case-study style; GT uses CHEBI+FOODON+FOBI)
    ("Is it safe for a pregnant woman to consume sodium benzoate preservative?", ["CHEBI", "FOODON", "FOBI"]),
]


def get_queries():
    assert len(QUERIES) == 50, len(QUERIES)
    return QUERIES
