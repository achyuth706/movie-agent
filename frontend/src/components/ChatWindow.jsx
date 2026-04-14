import { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import './ChatWindow.css';

const SUGGESTIONS = [
  'What is The Big Bang Theory about?',
  'How many seasons does Breaking Bad have?',
  'What are the ratings for Interstellar?',
];

/* ── Single clapperboard icon, used everywhere — scales via size prop ── */
function ClapperIcon({ size = 34 }) {
  return (
    <svg
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
    >
      <circle cx="20" cy="20" r="20" fill="#1a0d2e" />
      {/* Body */}
      <rect x="7" y="19" width="26" height="15" rx="2.5" fill="#241836" stroke="#c0181f" strokeWidth="1.5" />
      {/* Top bar */}
      <rect x="7" y="11" width="26" height="9" rx="2" fill="#160e24" stroke="#c0181f" strokeWidth="1.5" />
      {/* Diagonal stripes */}
      <clipPath id="slateClip">
        <rect x="8" y="11.5" width="24" height="8" rx="1.5" />
      </clipPath>
      <g clipPath="url(#slateClip)">
        <rect x="8" y="11.5" width="24" height="8" fill="#160e24" />
        <line x1="10" y1="11" x2="7"  y2="20" stroke="#c0181f" strokeWidth="3.5" strokeOpacity="0.9" />
        <line x1="16" y1="11" x2="13" y2="20" stroke="#c0181f" strokeWidth="3.5" strokeOpacity="0.9" />
        <line x1="22" y1="11" x2="19" y2="20" stroke="#c0181f" strokeWidth="3.5" strokeOpacity="0.9" />
        <line x1="28" y1="11" x2="25" y2="20" stroke="#c0181f" strokeWidth="3.5" strokeOpacity="0.9" />
        <line x1="34" y1="11" x2="31" y2="20" stroke="#c0181f" strokeWidth="3.5" strokeOpacity="0.9" />
      </g>
      {/* Play triangle */}
      <polygon points="17,23 17,31 25.5,27" fill="#c0181f" opacity="0.95" />
    </svg>
  );
}

function TypingIndicator() {
  return (
    <div className="message-row agent">
      <div className="bot-avatar">
        <ClapperIcon size={34} />
      </div>
      <div className="message-content">
        <div className="message-label">CineMind</div>
        <div className="message-bubble agent typing-bubble">
          <span className="dot" />
          <span className="dot" />
          <span className="dot" />
        </div>
      </div>
    </div>
  );
}

export default function ChatWindow({ messages, isLoading, isOnline, onSuggest }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const showSuggestions = messages.length === 1 && messages[0].role === 'agent' && !isLoading;

  return (
    <div className="chat-window">
      <header className="chat-header">
        <div className="chat-header-avatar">
          <ClapperIcon size={44} />
          <span className={`online-dot ${isOnline ? 'online' : 'offline'}`} />
        </div>
        <div className="chat-header-text">
          <span className="chat-header-title">CineMind</span>
          <span className="chat-header-status">
            <span className={`status-dot ${isOnline ? 'online' : 'offline'}`} />
            {isOnline ? 'Online' : 'Offline'} · Your personal movie &amp; TV guide
          </span>
        </div>
      </header>

      <div className="message-list">
        {messages.map((msg, i) => (
          <div key={i} className={`message-row ${msg.role}`}>
            {msg.role === 'agent' && (
              <div className="bot-avatar">
                <ClapperIcon size={34} />
              </div>
            )}
            <div className="message-content">
              <div className="message-label">
                {msg.role === 'user' ? 'You' : 'CineMind'}
              </div>
              <div className={`message-bubble ${msg.role}${msg.isError ? ' error' : ''}`}>
                {msg.role === 'agent' ? (
                  <ReactMarkdown>{msg.isError ? `⚠️ ${msg.content}` : msg.content}</ReactMarkdown>
                ) : (
                  msg.content
                )}
              </div>
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
