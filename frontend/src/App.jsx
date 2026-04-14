import { useState, useEffect } from 'react';
import axios from 'axios';
import ChatWindow from './components/ChatWindow';
import ChatInput from './components/ChatInput';
import './App.css';

const AGENT_URL  = 'http://localhost:8000/chat';
const HEALTH_URL = 'http://localhost:8000/health';

const WELCOME = {
  role: 'agent',
  content: "Hey! I'm CineMind — your personal guide to movies and TV. Ask me anything and I'll find your next obsession. 🎬",
};

export default function App() {
  const [messages, setMessages]       = useState([WELCOME]);
  const [isLoading, setIsLoading]     = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [inputValue, setInputValue]   = useState('');
  const [isOnline, setIsOnline]       = useState(false);

  /* ── Backend health check ── */
  useEffect(() => {
    async function check() {
      try {
        await axios.get(HEALTH_URL, { timeout: 3000 });
        setIsOnline(true);
      } catch {
        setIsOnline(false);
      }
    }
    check();
    const id = setInterval(check, 30_000);
    return () => clearInterval(id);
  }, []);

  async function handleSend(userText) {
    const text = userText.trim();
    if (!text || isLoading) return;

    setInputValue('');
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setIsLoading(true);

    try {
      const { data } = await axios.post(AGENT_URL, {
        message: text,
        chat_history: chatHistory,
      });

      const agentText = data.response;

      setMessages(prev => [...prev, { role: 'agent', content: agentText }]);
      setChatHistory(prev => [
        ...prev,
        { role: 'human', content: text },
        { role: 'ai',    content: agentText },
      ]);
    } catch (err) {
      const detail =
        err.response?.data?.detail ||
        (err.code === 'ERR_NETWORK'
          ? 'Cannot reach the agent server. Make sure it is running on port 8000.'
          : err.message) ||
        'Something went wrong. Please try again.';
      setMessages(prev => [
        ...prev,
        { role: 'agent', content: detail, isError: true },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <div className="app-layout">
        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          isOnline={isOnline}
          onSuggest={setInputValue}
        />
        <ChatInput
          value={inputValue}
          onChange={setInputValue}
          onSend={handleSend}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
}
