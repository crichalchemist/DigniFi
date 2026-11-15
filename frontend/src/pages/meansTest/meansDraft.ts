import {
  MEANS_LINE_43_LABEL_CHANGE,
  MEANS_LINE_43_LABEL_CHOICES,
  MEANS_LINE_43_LABEL_HAPPENED,
  MEANS_LINE_43_LABEL_PAPERS,
} from '../../constants/copy';

export interface ExplanationAnswers {
  happened: string;
  change: string;
  choices: string;
  papers: string;
}

/**
 * The aid's draft for line 43's box: each answer the filer gave on its own line after its label,
 * a line break inside an answer a space. A blank answer leaves its label out. Nothing else is added.
 */
export function assembleExplanation(answers: ExplanationAnswers): string {
  const parts: [string, string][] = [
    [MEANS_LINE_43_LABEL_HAPPENED, answers.happened],
    [MEANS_LINE_43_LABEL_CHANGE, answers.change],
    [MEANS_LINE_43_LABEL_CHOICES, answers.choices],
    [MEANS_LINE_43_LABEL_PAPERS, answers.papers],
  ];
  return parts
    .map(([label, answer]) => [label, answer.trim().replace(/\r?\n|\r/g, ' ')])
    .filter(([, answer]) => answer !== '')
    .map(([label, answer]) => `${label} ${answer}`)
    .join('\n');
}
