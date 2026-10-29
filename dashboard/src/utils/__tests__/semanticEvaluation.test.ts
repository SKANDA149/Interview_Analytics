import { describe, expect, it } from 'vitest';
import { getSemanticEvaluationDisplay } from '../semanticEvaluation';

describe('getSemanticEvaluationDisplay', () => {
  it('renders missing semantic evaluation as an explicit unavailable state', () => {
    const display = getSemanticEvaluationDisplay(null, {
      status: 'not_evaluated',
      reason: 'No rubric provided',
    });

    expect(display.value).toBe('Not evaluated');
    expect(display.reason).toBe('No rubric provided');
    expect(display.showProgress).toBe(false);
  });

  it('keeps historical numeric reports readable without presenting quality claims', () => {
    const display = getSemanticEvaluationDisplay(42, undefined);

    expect(display.label).toBe('Historical similarity');
    expect(display.value).toBe('42.0%');
    expect(display.reason).toContain('not a validated answer-quality score');
    expect(display.showProgress).toBe(false);
  });

  it('only renders a progress bar for an explicitly evaluated rubric score', () => {
    const display = getSemanticEvaluationDisplay(84.5, {
      status: 'evaluated',
      reason: null,
    });

    expect(display.label).toBe('Rubric reference alignment');
    expect(display.value).toBe('84.5%');
    expect(display.showProgress).toBe(true);
  });
});
