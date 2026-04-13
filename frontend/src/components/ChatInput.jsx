import { SendHorizonal } from 'lucide-react';
import './ChatInput.css';

export default function ChatInput({ value, onChange, onSend, isLoading }) {
  const canSend = value.trim().length > 0 && !isLoading;

  function handleSend() {
    if (!canSend) return;
    onSend(value.trim());
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="chat-input-bar">
      <div className="chat-input-inner">
        <input
          className="chat-input-field"
          type="text"
          placeholder="Ask me about any movie or TV show..."
          value={value}
          onChange={e => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          autoComplete="off"
          autoFocus
        />
        <button
          className="chat-send-btn"
          onClick={handleSend}
          disabled={!canSend}
          aria-label="Send message"
        >
          <SendHorizonal size={18} strokeWidth={2} />
        </button>
      </div>
    </div>
  );
}
