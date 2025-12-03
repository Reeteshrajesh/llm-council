import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage1.css';

export default function Stage1({ responses, toolOutputs }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!responses || responses.length === 0) {
    return null;
  }

  return (
    <div className="stage stage1">
      <h3 className="stage-title">Stage 1: Individual Responses</h3>

      <div className="tabs">
        {responses.map((resp, index) => (
          <button
            key={index}
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {resp.model.split('/')[1] || resp.model}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="model-name">{responses[activeTab].model}</div>
        <div className="response-text markdown-content">
          <ReactMarkdown>{responses[activeTab].response}</ReactMarkdown>
        </div>

        {toolOutputs && toolOutputs.length > 0 && (
          <div className="tool-outputs">
            <div className="tool-outputs-title">Tool context</div>
            <ul>
              {toolOutputs.map((item, idx) => (
                <li key={idx}>
                  <strong>{item.tool}:</strong> {item.result}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
