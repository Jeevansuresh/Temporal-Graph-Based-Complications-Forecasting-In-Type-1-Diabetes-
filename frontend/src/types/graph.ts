/**
 * T1D-CareGraph Schema Definitions
 * Covers 3 Distinct Clinical Knowledge Graphs (Kidney, Cardio, Retinopathy)
 * and the Temporal Patient Graph (TG) for Patient Profiles.
 */

// ==========================================
// 1. NODE TYPES & ONTOLOGY
// ==========================================

export type ConceptNodeType =
  | 'Concept'
  | 'Condition'
  | 'Context'
  | 'Measurement'
  | 'Behavior'
  | 'Finding'
  | 'Outcome'
  | 'Process_State'
  | 'Context_State';

export type TGNodeType =
  | 'Patient'
  | 'Visit'
  | 'Measurement';

export type DomainKGType =
  | 'Kidney_KG'
  | 'Cardio_KG'
  | 'Retinopathy_KG'
  | 'Temporal_Patient_Graph';

// ==========================================
// 2. RELATIONSHIP TYPES
// ==========================================

export type CKGRelationType =
  | 'CLINICAL_RELATIONSHIP'
  | 'PRODUCES'
  | 'SUPPORTED_BY'
  | 'INPUT_TO';

export type TGRelationType =
  | 'HAS_VISIT'
  | 'HAS_MEASUREMENT'
  | 'INSTANCE_OF'
  | 'OBSERVED_STATE'
  | 'NEXT_VISIT';

export type AllRelationType = CKGRelationType | TGRelationType;

// ==========================================
// 3. NODE INTERFACES
// ==========================================

/** CKG Concept Node (Kidney, Cardio, Retinopathy) */
export interface ConceptNode {
  name: string; // Unique primary key
  concept_id?: number | string;
  type: string; // e.g. Biomarker, RiskFactor, Condition, Complication
  synonyms?: string[];
  unit?: string;
  description?: string;
  labels?: string[]; // e.g. ["Concept", "Condition"]
}

/** CKG Rule Node */
export interface RuleNode {
  rule_id: string; // Unique primary key
  name?: string;
  trigger: string;
  logical_condition: string;
  temporal_requirement: string;
  output_concept?: string;
  evidence_id?: string;
}

/** CKG Evidence Provenance Node */
export interface EvidenceNode {
  evidence_id: string; // Unique primary key
  citation: string;
  year?: number;
  source_type: string;
  population?: string;
  summary?: string;
  url_doi?: string;
  evidence_strength?: string;
  audit_claim_type?: string;
  audit_clinical_claim?: string;
  audit_source?: string;
}

/** TG Patient Node (Patient Profile) */
export interface PatientNode {
  patient_id: string; // Unique primary key
  age: number;
  sex: 'M' | 'F';
  height_cm?: number;
  puberty_status?: string;
  t1d_diagnosis?: string;
  t1d_duration?: number;
  description?: string;
  synthetic_expected_risk_state?: string;
  baseline_cvd_context?: string;
  temporal_pattern?: string;
}

/** TG Temporal Visit Node */
export interface VisitNode {
  patient_id: string;
  date: string; // YYYY-MM-DD
  visit_id?: string;
  age?: number;
  t1d_duration?: number;
  weight_kg?: number;
  height_cm?: number;
  bmi?: number;
  systolic_bp?: number;
  diastolic_bp?: number;
  random_glucose?: number;
  fasting_glucose?: number;
  heart_rate_bpm?: number;
  smoking_status?: string;
  hypertension_status?: string;
  dyslipidemia?: string;
  known_ascvd?: boolean;
  known_cad?: boolean;
  ecg_abnormality?: boolean;
  cardiovascular_symptoms?: string;
  serum_creatinine?: number;
  total_cholesterol?: number;
  clinical_action?: string;
}

/** TG Measurement Observation Node */
export interface MeasurementNode {
  patient_id: string;
  date: string;
  concept: string; // Name of concept instance
  value?: number;
  unit?: string;
  stage_index?: number;
  stage_label?: string;
  visit_id?: string;
}

// ==========================================
// 4. RELATIONSHIP INTERFACES
// ==========================================

export interface ClinicalRelationshipEdge {
  source: string; // Concept name
  target: string; // Concept name
  relation: string; // e.g. INCREASES_RISK_OF, INDICATES, PREDICTS
  evidence_id?: string;
  population?: string;
  directionality?: 'positive' | 'negative' | 'bidirectional';
  confidence?: number;
  evidence_strength?: string;
}

export interface RuleProducesEdge {
  rule_id: string;
  output_concept: string;
}

export interface RuleSupportedByEdge {
  rule_id: string;
  evidence_id: string;
}

export interface ConceptInputToRuleEdge {
  input_concept: string;
  rule_id: string;
}

export interface TGEdge {
  source_id: string;
  target_id: string;
  rel_type: TGRelationType;
}

// ==========================================
// 5. GRAPH SCHEMAS BY DOMAIN
// ==========================================

export interface DomainGraphSchema {
  domain: DomainKGType;
  neo4j_labels: string[];
  relationship_types: string[];
  uniqueness_constraints: string[];
  key_concepts: string[];
}

export interface CompleteSystemGraphSchemas {
  kidney_kg: DomainGraphSchema;
  cardio_kg: DomainGraphSchema;
  retinopathy_kg: DomainGraphSchema;
  temporal_patient_graph: DomainGraphSchema;
}
