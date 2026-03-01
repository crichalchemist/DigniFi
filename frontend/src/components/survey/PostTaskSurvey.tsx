/**
 * Post-Task Survey — optional feedback after form generation.
 *
 * 3 Likert-scale questions (comprehension, dignity, confidence)
 * + 2 open-text questions (confusing, change).
 * Responses tracked via analytics — never blocks the user.
 */

import { useState } from 'react';
import { trackEvent } from '../../utils/analytics';
import { Button } from '../common';
import './PostTaskSurvey.css';

interface PostTaskSurveyProps {
  sessionId: number;
  onComplete: () => void;
}

const SCALE_QUESTIONS = [
  { id: 'comprehension', text: 'How easy was this to understand?' },
  { id: 'dignity', text: 'Did you feel respected while using this?' },
  { id: 'confidence', text: 'Would you feel confident filing these forms?' },
] as const;

const TEXT_QUESTIONS = [
  { id: 'confusing', text: 'What was confusing?' },
  { id: 'change', text: 'What would you change?' },
] as const;

export function PostTaskSurvey({ sessionId, onComplete }: PostTaskSurveyProps) {
  const [responses, setResponses] = useState<Record<string, string | number>>({});
  const [submitted, setSubmitted] = useState(false);

  const handleScaleChange = (questionId: string, value: number) => {
    setResponses((prev) => ({ ...prev, [questionId]: value }));
  };

  const handleTextChange = (questionId: string, value: string) => {
    setResponses((prev) => ({ ...prev, [questionId]: value }));
  };

  const handleSubmit = () => {
    const allQuestions = [...SCALE_QUESTIONS, ...TEXT_QUESTIONS];
    for (const q of allQuestions) {
      if (responses[q.id] !== undefined && responses[q.id] !== '') {
        trackEvent('survey_response', {
          question_id: q.id,
          value: responses[q.id],
          session_id: sessionId,
        });
      }
    }
    setSubmitted(true);
    setTimeout(onComplete, 2000);
  };

  if (submitted) {
    return (
      <div className="survey-thanks" role="status">
        <p>Thank you for your feedback. Your input helps us improve.</p>
      </div>
    );
  }

  return (
    <div className="post-task-survey" role="form" aria-label="Feedback survey">
      <h2 className="survey-title">Quick Feedback</h2>
      <p className="survey-intro">
        Your answers help us make DigniFi better. This is optional.
      </p>

      {SCALE_QUESTIONS.map((q) => (
        <fieldset key={q.id} className="survey-question">
          <legend>{q.text}</legend>
          <div className="survey-scale" role="radiogroup">
            {[1, 2, 3, 4, 5].map((n) => (
              <label key={n} className="survey-scale-option">
                <input
                  type="radio"
                  name={q.id}
                  value={n}
                  checked={responses[q.id] === n}
                  onChange={() => handleScaleChange(q.id, n)}
                />
                <span className="survey-scale-label">{n}</span>
              </label>
            ))}
          </div>
          <div className="survey-scale-anchors">
            <span>Not at all</span>
            <span>Very much</span>
          </div>
        </fieldset>
      ))}

      {TEXT_QUESTIONS.map((q) => (
        <div key={q.id} className="survey-question">
          <label htmlFor={`survey-${q.id}`}>{q.text}</label>
          <textarea
            id={`survey-${q.id}`}
            rows={3}
            value={(responses[q.id] as string) || ''}
            onChange={(e) => handleTextChange(q.id, e.target.value)}
          />
        </div>
      ))}

      <div className="survey-actions">
        <Button onClick={handleSubmit}>Submit Feedback</Button>
        <button
          type="button"
          className="survey-skip"
          onClick={onComplete}
        >
          Skip
        </button>
      </div>
    </div>
  );
}

export default PostTaskSurvey;
