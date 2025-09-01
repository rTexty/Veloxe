import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';

interface TestExample {
  category: string;
  message: string;
  user_profile: {
    name: string;
    age: number;
    emotion_tags: string[];
    topic_tags: string[];
  };
}

interface TestResult {
  response: string;
  token_count: number;
  blocks: string[];
  is_crisis: boolean;
  processing_time: number;
  error?: string;
}

interface PromptHistoryItem {
  id: number;
  prompt: string;
  changed_at: string;
  changed_by?: string;
  is_current: boolean;
}

export default function PromptTester() {
  const [prompt, setPrompt] = useState('');
  const [testMessage, setTestMessage] = useState('');
  const [selectedExample, setSelectedExample] = useState<TestExample | null>(null);
  const [examples, setExamples] = useState<TestExample[]>([]);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [promptHistory, setPromptHistory] = useState<PromptHistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    loadCurrentPrompt();
    loadExamples();
    loadPromptHistory();
  }, []);

  const loadCurrentPrompt = async () => {
    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch('/api/prompt/current', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setPrompt(data.prompt);
      }
    } catch (error) {
      console.error('Error loading current prompt:', error);
    }
  };

  const loadExamples = async () => {
    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch('/api/prompt/examples', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setExamples(data.examples);
      }
    } catch (error) {
      console.error('Error loading examples:', error);
    }
  };

  const testPrompt = async () => {
    if (!testMessage.trim()) {
      setMessage('Введите тестовое сообщение');
      return;
    }

    setLoading(true);
    setMessage('');
    
    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch('/api/prompt/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          prompt: prompt,
          test_message: testMessage,
          user_profile: selectedExample?.user_profile || null
        })
      });

      if (response.ok) {
        const result = await response.json();
        setTestResult(result);
        
        if (result.error) {
          setMessage(`❌ Ошибка тестирования: ${result.error}`);
        } else {
          setMessage(`✅ Тест завершен за ${result.processing_time}с`);
        }
      } else {
        setMessage('❌ Ошибка API при тестировании');
      }
    } catch (error) {
      console.error('Error testing prompt:', error);
      setMessage('❌ Сетевая ошибка при тестировании');
    } finally {
      setLoading(false);
    }
  };

  const savePrompt = async () => {
    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch('/api/settings/system_prompt', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          value: prompt,
          changed_by: 'admin'
        })
      });

      if (response.ok) {
        setMessage('✅ Промпт сохранен!');
        setTimeout(() => setMessage(''), 3000);
      } else {
        setMessage('❌ Ошибка сохранения промпта');
      }
    } catch (error) {
      console.error('Error saving prompt:', error);
      setMessage('❌ Ошибка сохранения');
    }
  };

  const selectExample = (example: TestExample) => {
    setSelectedExample(example);
    setTestMessage(example.message);
  };

  const loadPromptHistory = async () => {
    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch('/api/prompt/history', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setPromptHistory(data.history);
      }
    } catch (error) {
      console.error('Error loading prompt history:', error);
    }
  };

  const restorePrompt = async (historyItem: PromptHistoryItem) => {
    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch(`/api/prompt/restore/${historyItem.id}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setPrompt(data.prompt);
        setMessage(`✅ Prompt restored from ${new Date(historyItem.changed_at).toLocaleDateString()}`);
        setTimeout(() => setMessage(''), 3000);
        loadPromptHistory(); // Refresh history
      } else {
        setMessage('❌ Error restoring prompt');
      }
    } catch (error) {
      console.error('Error restoring prompt:', error);
      setMessage('❌ Network error while restoring prompt');
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">🧪 GPT Prompt Testing</h1>
        <div className="flex gap-3">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
          >
            📜 {showHistory ? 'Hide' : 'Show'} History
          </button>
          <button
            onClick={savePrompt}
            className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded"
          >
            💾 Save Prompt
          </button>
        </div>
      </div>

      {message && (
        <div className={`mb-4 p-3 rounded ${
          message.includes('❌') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
        }`}>
          {message}
        </div>
      )}

      {showHistory && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>📜 Prompt History (Last 5 Changes)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {promptHistory.map((item, index) => (
                <div
                  key={item.id}
                  className={`p-4 border rounded-lg ${item.is_current ? 'border-green-500 bg-green-50' : 'border-gray-200 bg-gray-50'}`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        item.is_current ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {item.is_current ? 'CURRENT' : `Version ${index + 1}`}
                      </span>
                      <span className="text-sm text-gray-500">
                        {new Date(item.changed_at).toLocaleString()}
                      </span>
                      <span className="text-sm text-blue-600">
                        by {item.changed_by || 'system'}
                      </span>
                    </div>
                    {!item.is_current && (
                      <button
                        onClick={() => restorePrompt(item)}
                        className="bg-blue-500 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm"
                      >
                        🔄 Restore
                      </button>
                    )}
                  </div>
                  <div className="bg-white p-3 rounded border text-sm font-mono max-h-32 overflow-y-auto">
                    {item.prompt.substring(0, 200)}...
                    <div className="text-xs text-gray-500 mt-1">
                      {item.prompt.length} characters
                    </div>
                  </div>
                </div>
              ))}
              {promptHistory.length === 0 && (
                <div className="text-center text-gray-500 py-4">
                  No prompt history available
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Prompt Editor */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>🤖 System Prompt</CardTitle>
            </CardHeader>
            <CardContent>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="w-full h-96 px-3 py-2 border rounded-md font-mono text-sm resize-vertical"
                placeholder="Введите system prompt для GPT..."
              />
              <div className="mt-2 text-sm text-gray-500">
                Символов: {prompt.length} | Строк: {prompt.split('\n').length}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>💬 Test Message</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <textarea
                value={testMessage}
                onChange={(e) => setTestMessage(e.target.value)}
                className="w-full h-24 px-3 py-2 border rounded-md"
                placeholder="Введите тестовое сообщение от пользователя..."
              />
              
              {selectedExample && (
                <div className="bg-blue-50 p-3 rounded border">
                  <div className="text-sm font-medium text-blue-800 mb-1">
                    📋 Selected: {selectedExample.category}
                  </div>
                  <div className="text-sm text-blue-600">
                    👤 {selectedExample.user_profile.name}, {selectedExample.user_profile.age} лет
                  </div>
                  <div className="text-xs text-blue-500 mt-1">
                    Эмоции: {selectedExample.user_profile.emotion_tags.join(', ')}
                  </div>
                </div>
              )}
              
              <button
                onClick={testPrompt}
                disabled={loading}
                className="w-full bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
              >
                {loading ? '🔄 Testing...' : '🚀 Test Prompt'}
              </button>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Examples and Results */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>📝 Test Examples</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {examples.map((example, index) => (
                  <div
                    key={index}
                    onClick={() => selectExample(example)}
                    className={`p-3 border rounded cursor-pointer hover:bg-gray-50 ${
                      selectedExample === example ? 'border-blue-500 bg-blue-50' : ''
                    }`}
                  >
                    <div className="font-medium text-sm">{example.category}</div>
                    <div className="text-sm text-gray-600 mt-1 truncate">
                      "{example.message}"
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      👤 {example.user_profile.name} • {example.user_profile.emotion_tags.length} эмоций
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {testResult && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  🎯 Test Result
                  <span className={`px-2 py-1 rounded text-xs ${
                    testResult.is_crisis ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                  }`}>
                    {testResult.is_crisis ? 'CRISIS' : 'NORMAL'}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {testResult.error ? (
                  <div className="bg-red-50 border border-red-200 rounded p-3">
                    <div className="text-red-800 font-medium">Error:</div>
                    <div className="text-red-600 text-sm mt-1">{testResult.error}</div>
                  </div>
                ) : (
                  <>
                    <div className="bg-gray-50 p-3 rounded">
                      <div className="text-sm font-medium text-gray-700 mb-2">GPT Response:</div>
                      <div className="whitespace-pre-wrap text-sm">{testResult.response}</div>
                    </div>

                    {testResult.blocks.length > 1 && (
                      <div>
                        <div className="text-sm font-medium text-gray-700 mb-2">Blocks ({testResult.blocks.length}):</div>
                        <div className="space-y-2">
                          {testResult.blocks.map((block, index) => (
                            <div key={index} className="bg-blue-50 p-2 rounded text-sm">
                              <span className="text-blue-600 font-mono">Block {index + 1}:</span> {block}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="flex justify-between text-sm text-gray-500">
                      <span>⏱️ {testResult.processing_time}s</span>
                      <span>🔤 {testResult.token_count} tokens</span>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}