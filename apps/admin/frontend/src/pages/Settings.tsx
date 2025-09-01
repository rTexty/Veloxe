import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';

interface Setting {
  id: number;
  key: string;
  category: string;
  string_value?: string;
  integer_value?: number;
  boolean_value?: boolean;
  json_value?: any;
  description?: string;
  is_active: boolean;
  changed_by?: string;
  changed_at?: string;
  created_at: string;
  updated_at: string;
}

interface SettingsByCategory {
  frequent: Setting[];
  expert: Setting[];
}

// Словарь переводов названий настроек
const settingTranslations: { [key: string]: string } = {
  // Частые настройки
  'daily_message_limit': 'Дневной лимит сообщений',
  'system_prompt': 'Системный промпт',
  'greeting_enabled': 'Включить GPT-генерируемые приветствия',
  'paywall_text': 'Текст пейволла',
  'subscription_plans': 'Планы подписки',
  'subscription_reminders_enabled': 'Включить напоминания об истечении подписки',
  'subscription_reminder_24h_template': 'Шаблон напоминания за 24 часа',
  'subscription_reminder_expiry_template': 'Шаблон напоминания в день истечения',
  'crisis_keywords': 'Ключевые слова кризиса',
  'crisis_response_text': 'Текст ответа при кризисе',
  'crisis_safety_phrase': 'Фраза безопасности при кризисе',
  'emotion_tags': 'Теги эмоций',
  'topic_tags': 'Теги тем',
  'ping_enabled': 'Включить пинги',
  'ping_templates': 'Шаблоны пингов',
  'policy_version': 'Версия политики',
  'privacy_policy_text': 'Текст политики конфиденциальности',
  'help_text': 'Текст справки',
  
  // Экспертные настройки
  'emotion_max': 'Максимум эмоций',
  'topic_max': 'Максимум тем',
  'memory_window_size': 'Размер окна памяти',
  'long_memory_enabled': 'Включить длинную память',
  'max_blocks_per_reply': 'Максимум блоков в ответе',
  'min_block_length': 'Минимальная длина блока',
  'delay_between_blocks_min': 'Мин. задержка между блоками',
  'delay_between_blocks_max': 'Макс. задержка между блоками',
  'gpt_model': 'GPT модель',
  'gpt_temperature': 'Температура GPT',
  'gpt_max_tokens': 'Максимум токенов GPT',
  'api_timeout': 'Таймаут API',
  'allowed_ping_hours_start': 'Начало разрешенных часов пинга',
  'allowed_ping_hours_end': 'Конец разрешенных часов пинга',
  'ping_frequency_hours': 'Частота пингов (часы)',
  'greeting_prompt': 'Промпт приветствия',
  'greeting_fallback_templates': 'Резервные шаблоны приветствия',
  'welcome_message': 'Приветственное сообщение для новых пользователей',
  'cryptocloud_api_key': 'CryptoCloud API Key',
  'cryptocloud_shop_id': 'CryptoCloud Shop ID',
  'support_contact': 'Контакт поддержки',
  'idle_ping_delay': 'Задержка внутрисессионного пинга (минуты)',
  'session_close_timeout': 'Таймаут закрытия сессии (часы)',
  'idle_ping_templates': 'Шаблоны внутрисессионных пингов'
};

// Функция для получения русского названия настройки
const getSettingDisplayName = (key: string): string => {
  return settingTranslations[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

// Категоризация настроек по вкладкам
const settingTabs = {
  basic: {
    title: '💬 Основные',
    description: 'Базовые настройки работы бота и взаимодействия с пользователями',
    settings: ['greeting_enabled', 'welcome_message', 'greeting_prompt', 'greeting_fallback_templates', 'help_text']
  },
  monetization: {
    title: '💳 Монетизация и Лимиты',
    description: 'Управление платными функциями, подписками и ограничениями',
    settings: ['daily_message_limit', 'subscription_plans', 'paywall_text', 'subscription_reminders_enabled', 'subscription_reminder_24h_template', 'subscription_reminder_expiry_template']
  },
  security: {
    title: '🛡️ Безопасность и Кризисные ситуации',
    description: 'Настройки безопасности пользователей и реакции на критические ситуации',
    settings: ['crisis_keywords', 'crisis_response_text', 'crisis_safety_phrase', 'privacy_policy_text', 'policy_version']
  },
  behavior: {
    title: '⚙️ Поведение и Контент',
    description: 'Настройки генерации ответов и категоризации контента',
    settings: ['emotion_tags', 'topic_tags', 'memory_window_size', 'long_memory_enabled', 'delay_between_blocks_min', 'delay_between_blocks_max']
  },
  pings: {
    title: '🔔 Пинги (Уведомления)',
    description: 'Настройки проактивных уведомлений от бота',
    settings: ['ping_enabled', 'ping_templates', 'ping_frequency_hours', 'allowed_ping_hours_start', 'allowed_ping_hours_end', 'idle_ping_delay', 'idle_ping_templates']
  },
  expert: {
    title: '🛠️ Экспертные настройки',
    description: 'Тонкая настройка модели и технические параметры',
    settings: ['gpt_model', 'gpt_temperature', 'gpt_max_tokens', 'api_timeout', 'max_blocks_per_reply', 'min_block_length', 'emotion_max', 'topic_max', 'cryptocloud_api_key', 'cryptocloud_shop_id', 'support_contact', 'session_close_timeout']
  }
};

// Функция для определения вкладки настройки
const getSettingTab = (settingKey: string): string => {
  for (const [tabKey, tabData] of Object.entries(settingTabs)) {
    if (tabData.settings.includes(settingKey)) {
      return tabKey;
    }
  }
  return 'expert'; // По умолчанию в экспертные
};

// Boolean настройки, которые должны быть переключателями
const booleanSettings = [
  'greeting_enabled',
  'subscription_reminders_enabled', 
  'ping_enabled',
  'long_memory_enabled'
];

// Функция для проверки, является ли настройка boolean
const isBooleanSetting = (settingKey: string): boolean => {
  return booleanSettings.includes(settingKey);
};

export default function Settings() {
  const [settings, setSettings] = useState<{[key: string]: Setting[]}>({});
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [activeTab, setActiveTab] = useState('basic');
  const [searchTerm, setSearchTerm] = useState('');
  const [previewData, setPreviewData] = useState<{key: string, preview: string, variables: string[]} | null>(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch('/api/settings/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data: Setting[] = await response.json();
        console.log('Loaded settings from server:', data.filter(s => isBooleanSetting(s.key)).map(s => ({
          key: s.key,
          boolean_value: s.boolean_value,
          string_value: s.string_value,
          calculated_value: isBooleanSetting(s.key) ? (
            s.boolean_value !== null && s.boolean_value !== undefined 
              ? s.boolean_value 
              : s.string_value === 'true' || s.string_value === 'True'
          ) : 'N/A'
        })));
        
        // Group settings by new tabs
        const settingsByTabs: {[key: string]: Setting[]} = {};
        
        // Initialize all tabs
        Object.keys(settingTabs).forEach(tabKey => {
          settingsByTabs[tabKey] = [];
        });
        
        // Group settings into tabs
        data.forEach(setting => {
          const tabKey = getSettingTab(setting.key);
          settingsByTabs[tabKey].push(setting);
        });
        
        setSettings(settingsByTabs);
      }
    } catch (error) {
      console.error('Error fetching settings:', error);
      setMessage('Error loading settings');
    }
  };

  const validateSetting = (setting: Setting, value: any): string | null => {
    // Validate based on setting key
    if (setting.key === 'daily_message_limit' && value < 1) {
      return 'Daily message limit must be at least 1';
    }
    
    if (setting.key === 'emotion_max' && (value < 1 || value > 50)) {
      return 'Emotion max must be between 1 and 50';
    }
    
    if (setting.key === 'topic_max' && (value < 1 || value > 50)) {
      return 'Topic max must be between 1 and 50';
    }
    
    if (setting.key === 'memory_window_size' && (value < 1 || value > 100)) {
      return 'Memory window size must be between 1 and 100';
    }
    
    if (setting.key === 'max_blocks_per_reply' && (value < 1 || value > 10)) {
      return 'Max blocks per reply must be between 1 and 10';
    }
    
    if (setting.key === 'delay_between_blocks_min' && value < 0) {
      return 'Delay cannot be negative';
    }
    
    if (setting.key === 'delay_between_blocks_max' && value < 0) {
      return 'Delay cannot be negative';
    }
    
    if (setting.key === 'api_timeout' && (value < 5 || value > 300)) {
      return 'API timeout must be between 5 and 300 seconds';
    }
    
    if (setting.key === 'allowed_ping_hours_start' && (value < 0 || value > 23)) {
      return 'Hours must be between 0 and 23';
    }
    
    if (setting.key === 'allowed_ping_hours_end' && (value < 0 || value > 23)) {
      return 'Hours must be between 0 and 23';
    }
    
    // Validate arrays
    if (Array.isArray(value)) {
      if (setting.key === 'crisis_keywords' && value.length === 0) {
        return 'Crisis keywords cannot be empty';
      }
      
      if (setting.key === 'emotion_tags' && value.length === 0) {
        return 'At least one emotion tag is required';
      }
      
      if (setting.key === 'topic_tags' && value.length === 0) {
        return 'At least one topic tag is required';
      }
    }
    
    // Validate required string fields
    if (typeof value === 'string') {
      if ((setting.key === 'crisis_response_text' || 
           setting.key === 'crisis_safety_phrase' ||
           setting.key === 'paywall_text') && 
          value.trim().length === 0) {
        return 'This field cannot be empty';
      }
      
      // Special validation for system prompt
      if (setting.key === 'system_prompt') {
        if (value.trim().length === 0) {
          return 'System prompt cannot be empty';
        }
        if (value.length < 50) {
          return 'System prompt is too short (minimum 50 characters)';
        }
        if (value.length > 4000) {
          return 'System prompt is too long (maximum 4000 characters)';
        }
        
        // Check for dangerous patterns
        const dangerousPatterns = [
          /ignore\s+(previous|all)\s+instructions?/i,
          /forget\s+(everything|all)/i,
          /you\s+are\s+now/i,
          /system\s+override/i,
          /admin\s+mode/i
        ];
        
        for (const pattern of dangerousPatterns) {
          if (pattern.test(value)) {
            return 'Prompt contains potentially dangerous instruction override patterns';
          }
        }
      }
    }
    
    return null; // Valid
  };

  const handleSave = async (setting: Setting) => {
    let value = getSettingValue(setting);
    
    // For boolean settings, ensure we send actual boolean value
    if (isBooleanSetting(setting.key)) {
      value = getSettingValue(setting);
    }
    
    console.log(`handleSave called for ${setting.key}:`, value, 'setting object:', setting);
    const validationError = validateSetting(setting, value);
    
    if (validationError) {
      setMessage(`Validation error: ${validationError}`);
      return;
    }
    
    setLoading(true);
    try {
      const token = localStorage.getItem('admin_token');
      
      console.log(`Sending to server:`, { value, changed_by: 'admin' });
      
      const response = await fetch(`/api/settings/${setting.key}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          value: value,
          changed_by: 'admin'
        })
      });
      
      if (response.ok) {
        // For boolean settings, just confirm the save was successful - state is already updated
        if (!isBooleanSetting(setting.key)) {
          setMessage(`✅ Настройка "${getSettingDisplayName(setting.key)}" успешно сохранена!`);
          setTimeout(() => setMessage(''), 3000);
          fetchSettings(); // Refresh settings for non-boolean settings
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        setMessage(`❌ Error saving setting: ${errorData.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error saving settings:', error);
      setMessage('❌ Network error while saving settings');
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = async (setting: Setting) => {
    try {
      const token = localStorage.getItem('admin_token');
      const sampleData = {
        name: 'Анна',
        day_part: 'утром',
        days: '3',
        limit: '10'
      };
      
      const response = await fetch(`/api/settings/${setting.key}/preview`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(sampleData)
      });
      
      if (response.ok) {
        const data = await response.json();
        setPreviewData({
          key: setting.key,
          preview: data.preview,
          variables: data.variables_used || []
        });
      } else {
        setMessage('❌ Ошибка при получении предпросмотра');
      }
    } catch (error) {
      console.error('Preview error:', error);
      setMessage('❌ Ошибка сети при получении предпросмотра');
    }
  };

  const getSettingValue = (setting: Setting) => {
    // For boolean settings, prioritize boolean_value and handle string representations
    if (isBooleanSetting(setting.key)) {
      if (setting.boolean_value !== null && setting.boolean_value !== undefined) {
        return setting.boolean_value;
      }
      // Handle string representations of booleans
      if (setting.string_value !== null && setting.string_value !== undefined) {
        return setting.string_value === 'true' || setting.string_value === 'True';
      }
      return false; // Default to false for boolean settings
    }
    
    if (setting.string_value !== null && setting.string_value !== undefined) return setting.string_value;
    if (setting.integer_value !== null && setting.integer_value !== undefined) return setting.integer_value;
    if (setting.boolean_value !== null && setting.boolean_value !== undefined) return setting.boolean_value;
    if (setting.json_value !== null && setting.json_value !== undefined) return setting.json_value;
    return '';
  };

  const updateSettingValue = (setting: Setting, value: any) => {
    const updatedSetting = { ...setting };
    
    // Clear all values first
    updatedSetting.string_value = undefined;
    updatedSetting.integer_value = undefined;
    updatedSetting.boolean_value = undefined;
    updatedSetting.json_value = undefined;
    
    // Set the appropriate value type
    if (typeof value === 'string') {
      updatedSetting.string_value = value;
    } else if (typeof value === 'number') {
      updatedSetting.integer_value = value;
    } else if (typeof value === 'boolean') {
      updatedSetting.boolean_value = value;
    } else {
      updatedSetting.json_value = value;
    }
    
    // Update settings state - find in all tabs
    const newSettings = { ...settings };
    let updated = false;
    
    for (const [tabKey, tabSettings] of Object.entries(newSettings)) {
      const index = tabSettings.findIndex(s => s.key === setting.key);
      if (index !== -1) {
        tabSettings[index] = updatedSetting;
        updated = true;
        break;
      }
    }
    
    if (updated) {
      setSettings(newSettings);
    }
  };

  // Component for rendering different setting types  
  const renderSettingInput = (setting: Setting) => {
    const value = getSettingValue(setting);
    
    // Boolean settings with toggle switches
    if (isBooleanSetting(setting.key)) {
      const boolValue = getSettingValue(setting) as boolean;
      
      const handleToggle = (checked: boolean) => {
        // Don't toggle if already in progress or same value
        if (checked === boolValue) return;
        
        // Update local state only - no auto-save
        updateSettingValue(setting, checked);
      };
      
      return (
        <div className="flex items-center" key={`${setting.key}-${boolValue}`}>
          <button
            type="button"
            onClick={() => handleToggle(!boolValue)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
              boolValue ? 'bg-blue-600' : 'bg-gray-200'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 rounded-full bg-white shadow transform transition-transform duration-200 ${
                boolValue ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      );
    }
    
    // String settings with special handling for long texts
    if (setting.string_value !== undefined && setting.string_value !== null) {
      const isLongText = setting.key.includes('text') || setting.key.includes('response') || 
                        setting.key.includes('policy') || setting.key.includes('help');
      const isPrompt = setting.key === 'system_prompt';
      
      // Special editor for system prompt
      if (isPrompt) {
        return (
          <div className="space-y-3">
            <textarea
              value={value as string}
              onChange={(e) => updateSettingValue(setting, e.target.value)}
              className="w-full px-3 py-2 border rounded-md resize-vertical font-mono text-sm h-64"
              placeholder="Введите system prompt для GPT..."
            />
            <div className="flex justify-between items-center text-sm text-gray-500">
              <span>Символов: {String(value).length} | Строк: {String(value).split('\n').length}</span>
              <a
                href="/prompt-tester"
                className="text-blue-500 hover:text-blue-700 font-medium"
              >
                🧪 Test this prompt
              </a>
            </div>
          </div>
        );
      }
      
      return (
        <textarea
          value={value as string}
          onChange={(e) => updateSettingValue(setting, e.target.value)}
          className={`w-full px-3 py-2 border rounded-md resize-vertical ${
            isLongText ? 'h-32' : 'h-20'
          }`}
          placeholder={`Введите ${getSettingDisplayName(setting.key).toLowerCase()}...`}
          rows={isLongText ? 6 : 3}
        />
      );
    }
    
    // Integer settings with smart ranges
    if (setting.integer_value !== undefined && setting.integer_value !== null) {
      let min = 0, max = 999999, step = 1;
      
      // Set smart defaults based on setting key
      if (setting.key.includes('limit') || setting.key.includes('max')) {
        min = 1;
        max = 100;
      } else if (setting.key.includes('delay') || setting.key.includes('timeout')) {
        min = 100;
        max = 60000;
        step = 100;
      } else if (setting.key.includes('hours')) {
        min = 0;
        max = 23;
      } else if (setting.key.includes('days')) {
        min = 1;
        max = 365;
      } else if (setting.key.includes('price')) {
        min = 1;
        max = 99999;
      }
      
      return (
        <div className="space-y-2">
          <input
            type="number"
            value={value as number}
            onChange={(e) => updateSettingValue(setting, Number(e.target.value))}
            className="w-full px-3 py-2 border rounded-md"
            min={min}
            max={max}
            step={step}
          />
          <div className="text-xs text-gray-500">
            Range: {min} - {max}
            {setting.key.includes('delay') && ' (milliseconds)'}
            {setting.key.includes('timeout') && ' (seconds)'}
            {setting.key.includes('days') && ' (days)'}
            {setting.key.includes('hours') && ' (0-23)'}
          </div>
        </div>
      );
    }
    
    // Boolean settings with better styling
    if (setting.boolean_value !== undefined && setting.boolean_value !== null) {
      return (
        <label className="flex items-center cursor-pointer">
          <div className="relative">
            <input
              type="checkbox"
              checked={value as boolean}
              onChange={(e) => updateSettingValue(setting, e.target.checked)}
              className="sr-only"
            />
            <div className={`block w-14 h-8 rounded-full ${
              value ? 'bg-blue-500' : 'bg-gray-300'
            } transition-colors`}></div>
            <div className={`absolute left-1 top-1 bg-white w-6 h-6 rounded-full transition-transform ${
              value ? 'transform translate-x-6' : ''
            }`}></div>
          </div>
          <span className={`ml-3 font-medium ${value ? 'text-green-600' : 'text-gray-500'}`}>
            {value ? 'Enabled' : 'Disabled'}
          </span>
        </label>
      );
    }
    
    // JSON settings (arrays and objects)
    if (setting.json_value !== undefined && setting.json_value !== null) {
      // Special handler for subscription plans
      if (setting.key === 'subscription_plans') {
        const plans = Array.isArray(value) ? value : [];
        return (
          <div className="space-y-3">
            {plans.map((plan: any, index: number) => (
              <div key={index} className="border rounded-lg p-3 bg-gray-50">
                <div className="grid grid-cols-2 gap-2 mb-2">
                  <input
                    type="text"
                    value={plan.name || ''}
                    placeholder="Plan name"
                    className="px-2 py-1 border rounded text-sm"
                    onChange={(e) => {
                      const newPlans = [...plans];
                      newPlans[index] = { ...plan, name: e.target.value };
                      updateSettingValue(setting, newPlans);
                    }}
                  />
                  <input
                    type="number"
                    value={plan.price || 0}
                    placeholder="Price"
                    className="px-2 py-1 border rounded text-sm"
                    onChange={(e) => {
                      const newPlans = [...plans];
                      newPlans[index] = { ...plan, price: Number(e.target.value) };
                      updateSettingValue(setting, newPlans);
                    }}
                  />
                  <input
                    type="number"
                    value={plan.days || 0}
                    placeholder="Days"
                    className="px-2 py-1 border rounded text-sm"
                    onChange={(e) => {
                      const newPlans = [...plans];
                      newPlans[index] = { ...plan, days: Number(e.target.value) };
                      updateSettingValue(setting, newPlans);
                    }}
                  />
                  <input
                    type="text"
                    value={plan.currency || 'RUB'}
                    placeholder="Currency"
                    className="px-2 py-1 border rounded text-sm"
                    onChange={(e) => {
                      const newPlans = [...plans];
                      newPlans[index] = { ...plan, currency: e.target.value };
                      updateSettingValue(setting, newPlans);
                    }}
                  />
                </div>
                <button
                  onClick={() => {
                    const newPlans = plans.filter((_, i) => i !== index);
                    updateSettingValue(setting, newPlans);
                  }}
                  className="text-red-500 hover:text-red-700 text-sm"
                >
                  Удалить план
                </button>
              </div>
            ))}
            <button
              onClick={() => {
                const newPlans = [...plans, { name: '', days: 30, price: 599, currency: 'RUB', discount: 0 }];
                updateSettingValue(setting, newPlans);
              }}
              className="bg-green-500 text-white px-3 py-1 rounded text-sm hover:bg-green-600"
            >
              Добавить план
            </button>
          </div>
        );
      }
      
      // Array settings (tags, keywords, templates)
      const jsonValue = Array.isArray(value) ? value : [];
      
      if (setting.key === 'emotion_tags' || setting.key === 'topic_tags' || 
          setting.key === 'crisis_keywords' || setting.key === 'ping_templates') {
        return (
          <div className="space-y-2">
            <div className="flex flex-wrap gap-2 mb-2">
              {jsonValue.map((item: string, index: number) => (
                <span
                  key={index}
                  className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm flex items-center"
                >
                  {item}
                  <button
                    onClick={() => {
                      const newArray = jsonValue.filter((_, i) => i !== index);
                      updateSettingValue(setting, newArray);
                    }}
                    className="ml-2 text-red-500 hover:text-red-700"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Добавить новый элемент..."
                className="flex-1 px-3 py-2 border rounded-md text-sm"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    const input = e.target as HTMLInputElement;
                    if (input.value.trim()) {
                      const newArray = [...jsonValue, input.value.trim()];
                      updateSettingValue(setting, newArray);
                      input.value = '';
                    }
                  }
                }}
              />
            </div>
          </div>
        );
      }
      
      // For other JSON settings, show as textarea
      return (
        <textarea
          value={JSON.stringify(value, null, 2)}
          onChange={(e) => {
            try {
              const parsed = JSON.parse(e.target.value);
              updateSettingValue(setting, parsed);
            } catch (error) {
              // Invalid JSON, don't update
            }
          }}
          className="w-full px-3 py-2 border rounded-md h-32 font-mono text-sm"
          placeholder="Enter JSON..."
        />
      );
    }
    
    return <div className="text-gray-500">Unknown setting type</div>;
  };

  const filteredSettings = (tabKey: string) => {
    if (!settings[tabKey]) return [];
    return settings[tabKey].filter(setting =>
      setting.key.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (setting.description && setting.description.toLowerCase().includes(searchTerm.toLowerCase())) ||
      getSettingDisplayName(setting.key).toLowerCase().includes(searchTerm.toLowerCase())
    );
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">⚙️ Управление настройками</h1>
        <div className="flex gap-4">
          <input
            type="text"
            placeholder="Поиск настроек..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="px-3 py-2 border rounded-md"
          />
        </div>
      </div>
      
      {message && (
        <div className={`mb-4 p-3 rounded ${message.includes('Error') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
          {message}
        </div>
      )}
      
      {/* Category Tabs */}
      <div className="flex flex-wrap gap-2 mb-6">
        {Object.entries(settingTabs).map(([tabKey, tabData]) => (
          <button
            key={tabKey}
            onClick={() => setActiveTab(tabKey)}
            className={`px-4 py-2 rounded-lg font-medium text-sm ${
              activeTab === tabKey
                ? 'bg-blue-500 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
            title={tabData.description}
          >
            {tabData.title} ({settings[tabKey]?.length || 0})
          </button>
        ))}
      </div>
      
      {/* Active Tab Description */}
      {settingTabs[activeTab as keyof typeof settingTabs] && (
        <div className="mb-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <h3 className="font-medium text-blue-900 mb-1">{settingTabs[activeTab as keyof typeof settingTabs].title}</h3>
          <p className="text-blue-700 text-sm">{settingTabs[activeTab as keyof typeof settingTabs].description}</p>
        </div>
      )}
      
      {/* Settings Cards */}
      <div className="space-y-4">
        {filteredSettings(activeTab).map((setting) => (
          <Card key={setting.id} className="w-full">
            <CardHeader className="pb-2">
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle className="text-lg">{getSettingDisplayName(setting.key)}</CardTitle>
                  {setting.description && (
                    <p className="text-sm text-gray-600 mt-1">{setting.description}</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    setting.category === 'frequent' 
                      ? 'bg-blue-100 text-blue-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {setting.category === 'frequent' ? 'Частые' : 'Экспертные'}
                  </span>
                  {setting.changed_at && (
                    <span className="text-xs text-gray-500">
                      Обновлено: {new Date(setting.changed_at).toLocaleDateString('ru-RU')}
                    </span>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {renderSettingInput(setting)}
              
              <div className="flex justify-between items-center">
                <div className="text-sm text-gray-500">
                  {setting.changed_by && `Last changed by: ${setting.changed_by}`}
                </div>
                <div className="flex gap-2">
                  {(setting.key.includes('template') || setting.key.includes('text') || 
                    setting.key.includes('response') || setting.key.includes('phrase')) && (
                    <button
                      onClick={() => handlePreview(setting)}
                      className="bg-green-500 hover:bg-green-700 text-white font-medium py-1 px-3 rounded text-sm"
                    >
                      🔍 Предпросмотр
                    </button>
                  )}
                  <button
                    onClick={() => handleSave(setting)}
                    disabled={loading}
                    className="bg-blue-500 hover:bg-blue-700 text-white font-medium py-1 px-3 rounded text-sm disabled:opacity-50"
                  >
                    {loading ? 'Сохранение...' : 'Сохранить'}
                  </button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
        
        {filteredSettings(activeTab).length === 0 && (
          <div className="text-center py-8 text-gray-500">
            Настройки не найдены {searchTerm && `по запросу "${searchTerm}"`}
          </div>
        )}
      </div>
      
      {/* Preview Modal */}
      {previewData && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full m-4">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">🔍 Предпросмотр: {getSettingDisplayName(previewData.key)}</h2>
              <button
                onClick={() => setPreviewData(null)}
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                ×
              </button>
            </div>
            
            <div className="space-y-4">
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="font-medium mb-2">Результат:</h3>
                <div className="bg-white border rounded p-3 whitespace-pre-wrap">
                  {previewData.preview}
                </div>
              </div>
              
              <div className="bg-blue-50 p-4 rounded-lg">
                <h3 className="font-medium mb-2">Использованные переменные:</h3>
                <div className="flex flex-wrap gap-2">
                  {previewData.variables.length > 0 ? (
                    previewData.variables.map((variable: string, index: number) => (
                      <span key={index} className="bg-blue-200 text-blue-800 px-2 py-1 rounded text-sm">
                        {`{${variable}}`}
                      </span>
                    ))
                  ) : (
                    <span className="text-gray-500 text-sm">Переменные не найдены</span>
                  )}
                </div>
              </div>
              
              <div className="text-sm text-gray-600">
                <strong>Доступные переменные:</strong> {'{name}'}, {'{day_part}'}, {'{days}'}, {'{limit}'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}