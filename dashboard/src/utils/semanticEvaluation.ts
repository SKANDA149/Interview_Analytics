import { SemanticEvaluation } from '../api/types';

export interface SemanticEvaluationDisplay {
  label: string;
  value: string;
  reason: string;
  showProgress: boolean;
}

/**
 * Make unavailable and historical semantic fields safe to display. Numeric
 * values are only described as rubric/reference alignment, never answer
 * correctness or interview quality.
 */
export function getSemanticEvaluationDisplay(
  score: number | null | undefined,
  evaluation?: SemanticEvaluation,
): SemanticEvaluationDisplay {
  if (evaluation?.status === 'evaluated' && typeof score === 'number') {
    return {
      label: 'Rubric reference alignment',
      value: `${score.toFixed(1)}%`,
      reason: 'Alignment with a supplied rubric; it is not an overall answer-quality score.',
      showProgress: true,
    };
  }

  if (
    (evaluation?.status === 'legacy_similarity' && typeof score === 'number') ||
    (typeof score === 'number' && !evaluation)
  ) {
    return {
      label: 'Historical similarity',
      value: `${score.toFixed(1)}%`,
      reason:
        evaluation?.reason ||
        'Preserved for compatibility. The rubric and response pairing are unknown, so this is not a validated answer-quality score.',
      showProgress: false,
    };
  }

  return {
    label: 'Semantic evaluation',
    value: 'Not evaluated',
    reason: evaluation?.reason || 'No rubric provided',
    showProgress: false,
  };
}
