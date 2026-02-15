export type DashboardMetrics = {
  total_pain_points: number;
  total_hours_per_week: number;
  top_categories: { category: string; count: number }[];
  team_heatmap: { team: string; categories: Record<string, number>; total: number }[];
  top_backlog: {
    pain_point_id: number;
    title: string;
    team: string;
    category: string;
    impact_hours_per_week: number;
    effort_score: number;
    confidence_score: number;
    priority_score: number;
    automation_type: string;
    suggested_solution: string;
    owner_suggestion: string;
  }[];
  quick_wins: {
    pain_point_id: number;
    title: string;
    team: string;
    impact_hours_per_week: number;
    priority_score: number;
  }[];
};

export type PainPointListItem = {
  id: number;
  title: string;
  category: string;
  team: string;
  role: string;
  priority_score: number | null;
  impact_hours_per_week: number | null;
  effort_score: number | null;
  confidence_score: number | null;
  quick_win: boolean;
  sensitive_flag: boolean;
};

export type PainPointDetail = {
  id: number;
  interview_id: number;
  respondent_id: number;
  team: string;
  role: string;
  title: string;
  description: string;
  category: string;
  frequency_per_week: number;
  minutes_per_occurrence: number;
  people_affected: number;
  systems_involved: string[];
  current_workaround: string | null;
  failure_modes: string | null;
  success_definition: string | null;
  sensitive_flag: boolean;
  redaction_notes: string | null;
  transcript_redacted: string | null;
  summary_text: string;
  score_id: number | null;
  impact_hours_per_week: number | null;
  effort_score: number | null;
  confidence_score: number | null;
  priority_score: number | null;
  quick_win: boolean;
  automation_type: string | null;
  suggested_solution: string | null;
  owner_suggestion: string | null;
  created_at: string;
};
