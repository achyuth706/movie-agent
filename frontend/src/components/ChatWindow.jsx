import { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import './ChatWindow.css';

const SUGGESTIONS = [
  'What is Inception about?',
  'How many seasons does Breaking Bad have?',
  'What are the ratings for Interstellar?',
];

function TypingIndicator() {
  return (
    <div className="message-row agent">
      <div className="message-label">Flick AI</div>
      <div className="message-bubble agent typing-bubble">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </div>
    </div>
  );
}

export default function ChatWindow({ messages, isLoading, onSuggest }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Show suggestion chips only while the conversation is still at the welcome message
  const showSuggestions = messages.length === 1 && messages[0].role === 'agent' && !isLoading;

  return (
    <div className="chat-window">
      <header className="chat-header">
        <span className="chat-header-icon">🎬</span>
        <div className="chat-header-text">
          <span className="chat-header-title">Flick AI</span>
          <span className="chat-header-tagline">Find your next obsession in seconds.</span>
        </div>
      </header>

      <div className="message-list">
        {messages.map((msg, i) => (
          <div key={i} className={`message-row ${msg.role}`}>
            <div className="message-label">
              {msg.role === 'user' ? 'You' : 'Flick AI'}
            </div>
            <div className={`message-bubble ${msg.role}${msg.isError ? ' error' : ''}`}>
              {msg.role === 'agent' ? (
                <ReactMarkdown>{msg.isError ? `⚠️ ${msg.content}` : msg.content}</ReactMarkdown>
              ) : (
                msg.content
              )}
            </div>
          </div>
        ))}

        {showSuggestions && (
          <div className="suggestions">
            <p className="suggestions-label">Try asking:</p>
            <div className="suggestions-chips">
              {SUGGESTIONS.map(s => (
                <button
                  key={s}
                  className="suggestion-chip"
                  onClick={() => onSuggest(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {isLoading && <TypingIndicator />}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
