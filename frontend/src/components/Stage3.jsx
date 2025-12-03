import ReactMarkdown from 'react-markdown';
import './Stage3.css';

export default function Stage3({ finalResponse, tokenSavings }) {
  if (!finalResponse) {
    return null;
  }

  return (
    <div className="stage stage3">
      <h3 className="stage-title">Stage 3: Final Council Answer</h3>
      <div className="final-response">
        <div className="chairman-label">
          Chairman: {finalResponse.model.split('/')[1] || finalResponse.model}
        </div>
        <div className="final-text markdown-content">
          <ReactMarkdown>{finalResponse.response}</ReactMarkdown>
        </div>

        {/* Display token savings if available */}
        {tokenSavings && tokenSavings.saved_tokens > 0 && (
          <div className="token-savings">
            💾 Saved {tokenSavings.saved_tokens.toLocaleString()} tokens
            ({tokenSavings.saved_percent}%) using TOON format
          </div>
        )}
      </div>
    </div>
  );
}
