import React, { useState, useEffect } from 'react';
import { X, Save, Loader2, Settings as SettingsIcon, Server, Key, Globe, User, Edit2, Trash2, Plus, Database, FileText } from 'lucide-react';
import axios from 'axios';

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
}

interface ProviderConfig {
    api_key?: string;
    model?: string;
    base_url?: string;
}

interface Persona {
    id: string;
    name: string;
    description: string;
    system_prompt: string;
}

interface Settings {
    theme: string;
    voice: string;
    active_provider: string;
    providers: {
        [key: string]: ProviderConfig;
    };
    active_persona_id: string;
    personas: Persona[];
    user_profile?: {
        name: string;
        about_me: string;
    };
    // Legacy
    api_key?: string;
}

const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
    const [settings, setSettings] = useState<Settings>({
        theme: 'dark',
        voice: 'default',
        active_provider: 'gemini',
        providers: {
            gemini: { api_key: '', model: 'gemini-2.5-flash-lite' },
            openai: { api_key: '', model: 'gpt-4o' },
            ollama: { base_url: 'http://localhost:11434', model: 'llama3' }
        },
        active_persona_id: 'default',
        personas: [],
        user_profile: { name: '', about_me: '' }
    });
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [editingPersona, setEditingPersona] = useState<Persona | null>(null);
    const [memories, setMemories] = useState<string[]>([]);
    const [loadingMemories, setLoadingMemories] = useState(false);

    useEffect(() => {
        if (isOpen) {
            fetchSettings();
            fetchMemories();
        }
    }, [isOpen]);

    const fetchMemories = async () => {
        setLoadingMemories(true);
        try {
            const response = await axios.get('http://localhost:8000/memories');
            setMemories(response.data.memories || []);
        } catch (error) {
            console.error('Failed to fetch memories:', error);
        } finally {
            setLoadingMemories(false);
        }
    };

    const handleClearMemories = async () => {
        if (!confirm('Are you sure you want to clear all long-term memories? This cannot be undone.')) return;
        try {
            await axios.delete('http://localhost:8000/memories');
            setMemories([]);
        } catch (error) {
            console.error('Failed to clear memories:', error);
        }
    };

    const handleClearKnowledgeBase = async () => {
        if (!confirm('Are you sure you want to clear the entire Knowledge Base (all uploaded documents)? This cannot be undone.')) return;
        try {
            await axios.delete('http://localhost:8000/knowledge');
            alert('Knowledge Base cleared successfully.');
        } catch (error) {
            console.error('Failed to clear knowledge base:', error);
            alert('Failed to clear knowledge base.');
        }
    };

    const fetchSettings = async () => {
        setLoading(true);
        try {
            const response = await axios.get('http://localhost:8000/settings');
            // Ensure providers object exists (migration for old settings)
            const data = response.data;
            if (!data.providers) {
                data.providers = {
                    gemini: { api_key: data.api_key || '', model: 'gemini-2.5-flash-lite' },
                    openai: { api_key: '', model: 'gpt-4o' },
                    ollama: { base_url: 'http://localhost:11434', model: 'llama3' }
                };
                data.active_provider = 'gemini';
            }
            if (!data.personas) {
                data.personas = [
                    { id: 'default', name: 'K', description: 'Your helpful AI assistant.', system_prompt: 'You are a helpful AI assistant.' }
                ];
                data.active_persona_id = 'default';
            }
            setSettings(data);
        } catch (error) {
            console.error('Failed to fetch settings:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            await axios.post('http://localhost:8000/settings', settings);
            window.dispatchEvent(new Event("settingsChanged"));
            onClose();
        } catch (error) {
            console.error('Failed to save settings:', error);
        } finally {
            setSaving(false);
        }
    };

    const updateProviderSetting = (provider: string, key: string, value: string) => {
        setSettings(prev => ({
            ...prev,
            providers: {
                ...prev.providers,
                [provider]: {
                    ...prev.providers[provider],
                    [key]: value
                }
            }
        }));
    };

    const handleSavePersona = () => {
        if (!editingPersona) return;

        setSettings(prev => {
            const existingIndex = prev.personas.findIndex(p => p.id === editingPersona.id);
            let newPersonas = [...prev.personas];

            if (existingIndex >= 0) {
                newPersonas[existingIndex] = editingPersona;
            } else {
                newPersonas.push(editingPersona);
            }

            return { ...prev, personas: newPersonas };
        });
        setEditingPersona(null);
    };

    const handleDeletePersona = (id: string) => {
        if (id === 'default') return; // Cannot delete default
        setSettings(prev => ({
            ...prev,
            personas: prev.personas.filter(p => p.id !== id),
            active_persona_id: prev.active_persona_id === id ? 'default' : prev.active_persona_id
        }));
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="w-full max-w-2xl rounded-2xl border border-white/10 bg-neutral-900 p-0 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
                {/* Header */}
                <div className="flex items-center justify-between border-b border-white/10 p-6 bg-neutral-800/50">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-purple-500/20 text-purple-400">
                            <SettingsIcon size={24} />
                        </div>
                        <h2 className="text-xl font-semibold text-white">Settings</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="rounded-full p-2 text-neutral-400 hover:bg-white/10 hover:text-white transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    {loading ? (
                        <div className="flex h-40 items-center justify-center">
                            <Loader2 className="animate-spin text-purple-500" size={32} />
                        </div>
                    ) : (
                        <div className="space-y-8">
                            {/* General Settings Section */}
                            <section className="space-y-4">
                                <h3 className="text-sm font-medium text-purple-400 uppercase tracking-wider">Appearance & Voice</h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="mb-2 block text-sm font-medium text-neutral-300">Theme</label>
                                        <select
                                            value={settings.theme}
                                            onChange={(e) => setSettings({ ...settings, theme: e.target.value })}
                                            className="w-full rounded-lg border border-white/10 bg-neutral-800 p-2.5 text-white focus:border-purple-500 focus:outline-none"
                                        >
                                            <option value="dark">Dark</option>
                                            <option value="light">Light</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="mb-2 block text-sm font-medium text-neutral-300">Voice</label>
                                        <select
                                            value={settings.voice}
                                            onChange={(e) => setSettings({ ...settings, voice: e.target.value })}
                                            className="w-full rounded-lg border border-white/10 bg-neutral-800 p-2.5 text-white focus:border-purple-500 focus:outline-none"
                                        >
                                            <option value="default">Default</option>
                                            <option value="alloy">Alloy</option>
                                            <option value="echo">Echo</option>
                                            <option value="fable">Fable</option>
                                            <option value="onyx">Onyx</option>
                                            <option value="nova">Nova</option>
                                            <option value="shimmer">Shimmer</option>
                                        </select>
                                    </div>
                                </div>
                            </section>

                            {/* Memory Management Section */}
                            <section className="space-y-4">
                                <h3 className="text-sm font-medium text-purple-400 uppercase tracking-wider">Long-Term Memory</h3>
                                <div className="p-4 rounded-xl bg-neutral-800/50 border border-white/5 space-y-4">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2 text-neutral-300">
                                            <Database size={16} />
                                            <span className="text-sm font-medium">Stored Memories</span>
                                        </div>
                                        <button
                                            onClick={handleClearMemories}
                                            disabled={memories.length === 0}
                                            className="text-xs flex items-center gap-1 text-red-400 hover:text-red-300 disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            <Trash2 size={14} /> Clear All
                                        </button>
                                    </div>

                                    <div className="max-h-40 overflow-y-auto rounded-lg border border-white/5 bg-neutral-900/50 p-3">
                                        {loadingMemories ? (
                                            <div className="flex justify-center p-4">
                                                <Loader2 className="animate-spin text-purple-500" size={20} />
                                            </div>
                                        ) : memories.length > 0 ? (
                                            <ul className="space-y-2">
                                                {memories.map((memory, index) => (
                                                    <li key={index} className="text-sm text-neutral-400 flex items-start gap-2">
                                                        <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-purple-500/50" />
                                                        <span>{memory}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        ) : (
                                            <div className="text-center text-sm text-neutral-500 py-4">
                                                No long-term memories stored yet.
                                            </div>
                                        )}
                                    </div>

                                    {/* Knowledge Base Management */}
                                    <div className="pt-4 border-t border-white/5 flex items-center justify-between">
                                        <div className="flex items-center gap-2 text-neutral-300">
                                            <FileText size={16} />
                                            <span className="text-sm font-medium">Knowledge Base (Documents)</span>
                                        </div>
                                        <button
                                            onClick={handleClearKnowledgeBase}
                                            className="text-xs flex items-center gap-1 text-red-400 hover:text-red-300"
                                        >
                                            <Trash2 size={14} /> Clear Documents
                                        </button>
                                    </div>
                                </div>
                            </section>

                            {/* User Profile Section */}
                            <section className="space-y-4">
                                <h3 className="text-sm font-medium text-purple-400 uppercase tracking-wider">User Profile</h3>
                                <div className="p-4 rounded-xl bg-neutral-800/50 border border-white/5 space-y-4">
                                    <div>
                                        <label className="mb-2 block text-sm font-medium text-neutral-300">Your Name</label>
                                        <input
                                            type="text"
                                            value={settings.user_profile?.name || ''}
                                            onChange={(e) => setSettings({
                                                ...settings,
                                                user_profile: {
                                                    ...(settings.user_profile || { name: '', about_me: '' }),
                                                    name: e.target.value
                                                }
                                            })}
                                            placeholder="What should I call you?"
                                            className="w-full rounded-lg border border-white/10 bg-neutral-900 p-2.5 text-white placeholder-neutral-600 focus:border-purple-500 focus:outline-none"
                                        />
                                    </div>
                                    <div>
                                        <label className="mb-2 block text-sm font-medium text-neutral-300">About You</label>
                                        <textarea
                                            value={settings.user_profile?.about_me || ''}
                                            onChange={(e) => setSettings({
                                                ...settings,
                                                user_profile: {
                                                    ...(settings.user_profile || { name: '', about_me: '' }),
                                                    about_me: e.target.value
                                                }
                                            })}
                                            rows={3}
                                            placeholder="Tell me about yourself (e.g., 'I am a software engineer', 'I prefer concise answers')..."
                                            className="w-full rounded-lg border border-white/10 bg-neutral-900 p-2.5 text-white placeholder-neutral-600 focus:border-purple-500 focus:outline-none resize-none"
                                        />
                                    </div>
                                </div>
                            </section>

                            {/* Persona Section */}
                            <section className="space-y-4">
                                <h3 className="text-sm font-medium text-purple-400 uppercase tracking-wider">Personality</h3>
                                <div className="p-4 rounded-xl bg-neutral-800/50 border border-white/5 space-y-4">
                                    <div className="flex items-center justify-between">
                                        <label className="block text-sm font-medium text-neutral-300">Active Persona</label>
                                        <button
                                            onClick={() => setEditingPersona({ id: crypto.randomUUID(), name: 'New Persona', description: '', system_prompt: '' })}
                                            className="text-xs flex items-center gap-1 text-purple-400 hover:text-purple-300"
                                        >
                                            <Plus size={14} /> Create New
                                        </button>
                                    </div>

                                    <div className="grid grid-cols-1 gap-3">
                                        {settings.personas.map(persona => (
                                            <div
                                                key={persona.id}
                                                className={`relative flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all ${settings.active_persona_id === persona.id
                                                    ? 'bg-purple-500/10 border-purple-500/50'
                                                    : 'bg-neutral-900 border-white/5 hover:border-white/10'
                                                    }`}
                                                onClick={() => setSettings({ ...settings, active_persona_id: persona.id })}
                                            >
                                                <div className="flex items-center gap-3">
                                                    <div className={`p-2 rounded-full ${settings.active_persona_id === persona.id ? 'bg-purple-500 text-white' : 'bg-neutral-800 text-neutral-400'}`}>
                                                        <User size={16} />
                                                    </div>
                                                    <div>
                                                        <div className="font-medium text-white text-sm">{persona.name}</div>
                                                        <div className="text-xs text-neutral-400">{persona.description}</div>
                                                    </div>
                                                </div>

                                                <div className="flex items-center gap-1">
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); setEditingPersona(persona); }}
                                                        className="p-1.5 text-neutral-400 hover:text-white hover:bg-white/10 rounded"
                                                    >
                                                        <Edit2 size={14} />
                                                    </button>
                                                    {persona.id !== 'default' && (
                                                        <button
                                                            onClick={(e) => { e.stopPropagation(); handleDeletePersona(persona.id); }}
                                                            className="p-1.5 text-neutral-400 hover:text-red-400 hover:bg-red-500/10 rounded"
                                                        >
                                                            <Trash2 size={14} />
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </section>

                            {/* AI Provider Section */}
                            <section className="space-y-4">
                                <h3 className="text-sm font-medium text-purple-400 uppercase tracking-wider">AI Model Provider</h3>

                                <div className="p-4 rounded-xl bg-neutral-800/50 border border-white/5 space-y-4">
                                    <div>
                                        <label className="mb-2 block text-sm font-medium text-neutral-300">Active Provider</label>
                                        <select
                                            value={settings.active_provider}
                                            onChange={(e) => setSettings({ ...settings, active_provider: e.target.value })}
                                            className="w-full rounded-lg border border-white/10 bg-neutral-800 p-2.5 text-white focus:border-purple-500 focus:outline-none"
                                        >
                                            <option value="gemini">Google Gemini</option>
                                            <option value="ollama">Ollama (Local)</option>
                                            <option value="openai">OpenAI (Coming Soon)</option>
                                        </select>
                                    </div>

                                    {/* Dynamic Provider Settings */}
                                    <div className="pt-4 border-t border-white/10">
                                        {settings.active_provider === 'gemini' && (
                                            <div className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
                                                <div className="flex items-center gap-2 text-sm text-neutral-400 mb-2">
                                                    <Key size={16} />
                                                    <span>Gemini Configuration</span>
                                                </div>
                                                <div>
                                                    <label className="mb-2 block text-sm font-medium text-neutral-300">API Key</label>
                                                    <input
                                                        type="password"
                                                        value={settings.providers?.gemini?.api_key || ''}
                                                        onChange={(e) => updateProviderSetting('gemini', 'api_key', e.target.value)}
                                                        placeholder="Enter Gemini API Key"
                                                        className="w-full rounded-lg border border-white/10 bg-neutral-900 p-2.5 text-white placeholder-neutral-600 focus:border-purple-500 focus:outline-none"
                                                    />
                                                </div>
                                                <div>
                                                    <label className="mb-2 block text-sm font-medium text-neutral-300">Model</label>
                                                    <input
                                                        type="text"
                                                        value={settings.providers?.gemini?.model || 'gemini-2.5-flash-lite'}
                                                        onChange={(e) => updateProviderSetting('gemini', 'model', e.target.value)}
                                                        className="w-full rounded-lg border border-white/10 bg-neutral-900 p-2.5 text-white placeholder-neutral-600 focus:border-purple-500 focus:outline-none"
                                                    />
                                                </div>
                                            </div>
                                        )}

                                        {settings.active_provider === 'ollama' && (
                                            <div className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
                                                <div className="flex items-center gap-2 text-sm text-neutral-400 mb-2">
                                                    <Server size={16} />
                                                    <span>Ollama Configuration</span>
                                                </div>
                                                <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 text-sm text-blue-200">
                                                    Ensure Ollama is running locally: <code>ollama serve</code>
                                                </div>
                                                <div>
                                                    <label className="mb-2 block text-sm font-medium text-neutral-300">Base URL</label>
                                                    <input
                                                        type="text"
                                                        value={settings.providers?.ollama?.base_url || 'http://localhost:11434'}
                                                        onChange={(e) => updateProviderSetting('ollama', 'base_url', e.target.value)}
                                                        placeholder="http://localhost:11434"
                                                        className="w-full rounded-lg border border-white/10 bg-neutral-900 p-2.5 text-white placeholder-neutral-600 focus:border-purple-500 focus:outline-none"
                                                    />
                                                </div>
                                                <div>
                                                    <label className="mb-2 block text-sm font-medium text-neutral-300">Model Name</label>
                                                    <input
                                                        type="text"
                                                        value={settings.providers?.ollama?.model || 'llama3'}
                                                        onChange={(e) => updateProviderSetting('ollama', 'model', e.target.value)}
                                                        placeholder="e.g., llama3, mistral"
                                                        className="w-full rounded-lg border border-white/10 bg-neutral-900 p-2.5 text-white placeholder-neutral-600 focus:border-purple-500 focus:outline-none"
                                                    />
                                                </div>
                                            </div>
                                        )}

                                        {settings.active_provider === 'openai' && (
                                            <div className="p-4 text-center text-neutral-400">
                                                OpenAI support is planned for a future update.
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </section>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="border-t border-white/10 p-6 bg-neutral-800/50">
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="flex w-full items-center justify-center gap-2 rounded-xl bg-purple-600 py-3 font-medium text-white hover:bg-purple-700 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100 shadow-lg shadow-purple-500/20"
                    >
                        {saving ? (
                            <Loader2 className="animate-spin" size={20} />
                        ) : (
                            <Save size={20} />
                        )}
                        Save Changes
                    </button>
                </div>
            </div>

            {/* Persona Editor Modal Overlay */}
            {editingPersona && (
                <div className="absolute inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
                    <div className="w-full max-w-lg rounded-xl border border-white/10 bg-neutral-900 p-6 shadow-2xl">
                        <h3 className="text-lg font-semibold text-white mb-4">
                            {editingPersona.id === 'default' ? 'View Persona' : 'Edit Persona'}
                        </h3>
                        <div className="space-y-4">
                            <div>
                                <label className="mb-2 block text-sm font-medium text-neutral-300">Name</label>
                                <input
                                    type="text"
                                    value={editingPersona.name}
                                    onChange={(e) => setEditingPersona({ ...editingPersona, name: e.target.value })}
                                    className="w-full rounded-lg border border-white/10 bg-neutral-800 p-2.5 text-white focus:border-purple-500 focus:outline-none"
                                    disabled={editingPersona.id === 'default'}
                                />
                            </div>
                            <div>
                                <label className="mb-2 block text-sm font-medium text-neutral-300">Description</label>
                                <input
                                    type="text"
                                    value={editingPersona.description}
                                    onChange={(e) => setEditingPersona({ ...editingPersona, description: e.target.value })}
                                    className="w-full rounded-lg border border-white/10 bg-neutral-800 p-2.5 text-white focus:border-purple-500 focus:outline-none"
                                    disabled={editingPersona.id === 'default'}
                                />
                            </div>
                            <div>
                                <label className="mb-2 block text-sm font-medium text-neutral-300">System Prompt</label>
                                <textarea
                                    value={editingPersona.system_prompt}
                                    onChange={(e) => setEditingPersona({ ...editingPersona, system_prompt: e.target.value })}
                                    rows={6}
                                    className="w-full rounded-lg border border-white/10 bg-neutral-800 p-2.5 text-white focus:border-purple-500 focus:outline-none resize-none font-mono text-sm"
                                    disabled={editingPersona.id === 'default'}
                                />
                            </div>
                            <div className="flex justify-end gap-2 mt-6">
                                <button
                                    onClick={() => setEditingPersona(null)}
                                    className="px-4 py-2 rounded-lg text-neutral-300 hover:bg-white/5"
                                >
                                    Cancel
                                </button>
                                {editingPersona.id !== 'default' && (
                                    <button
                                        onClick={handleSavePersona}
                                        className="px-4 py-2 rounded-lg bg-purple-600 text-white hover:bg-purple-700"
                                    >
                                        Save Persona
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default SettingsModal;
