import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import './App.css';

const BOT_AVATAR = "https://api.dicebear.com/9.x/bottts-neutral/svg?seed=BatteryBot";
const USER_AVATAR = "https://api.dicebear.com/9.x/adventurer-neutral/svg?seed=User123";

function App() {
  // 状态管理
  const [messages, setMessages] = useState([
    { role: 'bot', text: 'Hi! I’m your EV battery assistant. Do you have any questions about battery health, SOH, or charging?' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState('');
  
  // 引用：用于自动滚动到底部
  const messagesEndRef = useRef(null); // 改成 null

  // 1. 初始化：生成一个随机的 conversation_id
  useEffect(() => {
    const newId = 'conv_' + Math.random().toString(36).substr(2, 9);
    setConversationId(newId);
  }, []);

  // 2. 自动滚动：每当 messages 变化时，滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 3. 发送消息逻辑
  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = input;
    setInput(''); // 清空输入框
    
    // 添加用户消息到界面
    setMessages(prev => [...prev, { role: 'user', text: userMessage }]);
    setIsLoading(true);

    try {
      // 调用后端 API (注意：这里假设后端在 localhost:8000)
      const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
      const response = await fetch(`${API_URL}/chat-input`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: conversationId,
          message: userMessage
        })
      });

      const data = await response.json();

      if (response.ok) {
        // 添加机器人回复到界面
        setMessages(prev => [
          ...prev, 
          { 
            role: 'bot', 
            text: data.response, 
            sources: data.sources // 后端返回的参考来源
          }
        ]);
      } else {
        throw new Error('API Error');
      }

    } catch (error) {
      console.error("Error:", error);
      setMessages(prev => [...prev, { role: 'bot', text: '⚠️ 抱歉，连接后端时出现错误，请确保后端已启动。' }]);
    } finally {
      setIsLoading(false);
    }
  };

  // 允许按回车发送
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') handleSend();
  };

  return (
    <div className="app-container">
      <header className="chat-header">
        <h1>🔋 Battery AI Expert</h1>
      </header>

      <div className="messages-area">
        {messages.map((msg, index) => (
          <div key={index} className={`message-row ${msg.role}`}>
            {/* 1. 如果是机器人，头像显示在左边 */}
            {msg.role === 'bot' && (
              <img src={BOT_AVATAR} alt="Bot" className="avatar bot-avatar" />
            )}

            <div className="message-bubble">
              <ReactMarkdown>{msg.text}</ReactMarkdown>
              {msg.sources && msg.sources.length > 0 && (
                <div className="sources">
                  <small>📚 Sources: {msg.sources.join(', ')}</small>
                </div>
              )}
            </div>

            {/* 2. 如果是用户，头像显示在右边 */}
            {msg.role === 'user' && (
              <img src={USER_AVATAR} alt="User" className="avatar user-avatar" />
            )}
          </div>
        ))}
        
        {isLoading && (
          <div className="message-row bot">
            <img src={BOT_AVATAR} alt="Bot" className="avatar bot-avatar" />
            <div className="message-bubble loading">
              Thinking...
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Ask about EV batteries..."
          disabled={isLoading}
        />
        <button onClick={handleSend} disabled={isLoading}>
          Send
        </button>
      </div>
    </div>
  );
}

export default App;