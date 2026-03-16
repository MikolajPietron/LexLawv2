'use client';

import React, { useState } from 'react';
import { useUser, useSession, useClerk, useReverification } from '@clerk/nextjs';
import { isReverificationCancelledError } from '@clerk/nextjs/errors';
import {
  X,
  User,
  Shield,
  Sparkles,
  Camera,
  Pencil,
  Check,
  XIcon,
  Monitor,
  Smartphone,
  ChevronRight,
  LogOut,
  KeyRound,
  Eye,
  EyeOff,
} from 'lucide-react';
import Link from 'next/link';

type Tab = 'profile' | 'security' | 'tier';

interface ProfileModalProps {
  open: boolean;
  onClose: () => void;
}

export default function ProfileModal({ open, onClose }: ProfileModalProps) {
  const { user } = useUser();
  const { session } = useSession();
  const { signOut } = useClerk();
  const [activeTab, setActiveTab] = useState<Tab>('profile');

  // Editable fields
  const [editingField, setEditingField] = useState<string | null>(null);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [username, setUsername] = useState('');
  const [saving, setSaving] = useState(false);

  // Password
  const [showPassword, setShowPassword] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const tier = (user?.publicMetadata as any)?.tier || 'free';
const isPro = tier === 'pro';
    const updateUser = useReverification(async (params: { firstName?: string; lastName?: string; username?: string }) => {
    return user?.update(params);
  });

  const updatePassword = useReverification(async (params: { currentPassword: string; newPassword: string }) => {
    return user?.updatePassword(params);
  });

  

  if (!open || !user) return null;
  


  const startEdit = (field: string) => {
    setEditingField(field);
    if (field === 'name') {
      setFirstName(user.firstName || '');
      setLastName(user.lastName || '');
    }
    if (field === 'username') {
      setUsername(user.username || '');
    }
  };

  const cancelEdit = () => {
    setEditingField(null);
  };
    
  const saveName = async () => {
    setSaving(true);
    try {
      await updateUser({ firstName, lastName });
      setEditingField(null);
    } catch (e) {
      if (!isReverificationCancelledError(e)) console.error(e);
    }
    setSaving(false);
  };

  const saveUsername = async () => {
    setSaving(true);
    try {
      await updateUser({ username });
      setEditingField(null);
    } catch (e) {
      if (!isReverificationCancelledError(e)) console.error(e);
    }
    setSaving(false);
  };

  const handleChangePassword = async () => {
    setPasswordError('');
    setPasswordSuccess(false);
    if (newPassword.length < 8) {
      setPasswordError('Password must be at least 8 characters');
      return;
    }
    setSaving(true);
    try {
      await updatePassword({ currentPassword, newPassword });
      setPasswordSuccess(true);
      setCurrentPassword('');
      setNewPassword('');
      setShowPassword(false);
    } catch (e: any) {
      if (!isReverificationCancelledError(e)) {
        setPasswordError(e?.errors?.[0]?.message || 'Failed to update password');
      }
    }
    setSaving(false);
  };
  const handleManageBilling = async () => {
  setSaving(true);
  try {
    const token = await session?.getToken();
    if (!token) return;
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/create-portal-session`,
      {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    const data = await res.json();
    if (data.url) window.location.href = data.url;
  } catch (e) {
    console.error(e);
  }
  setSaving(false);
};

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'profile', label: 'Profile', icon: <User className="w-4 h-4" /> },
    { id: 'security', label: 'Security', icon: <Shield className="w-4 h-4" /> },
    { id: 'tier', label: 'Tier', icon: <Sparkles className="w-4 h-4" /> },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        style={{ animation: 'modalOverlayIn 0.3s ease-out' }}
        onClick={onClose}
      />

      {/* Panel */}
      <div
        className="relative w-full max-w-2xl max-h-[calc(100vh-120px)] rounded-2xl bg-black/80 backdrop-blur-xl border border-white/[0.08] overflow-hidden flex shadow-2xl shadow-black/60"
        style={{ animation: 'modalDrawerUp 0.5s cubic-bezier(0.16, 1, 0.3, 1)' }}
      >
        {/* Orange glow at top */}
        <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-[#e05929] to-transparent" />

        {/* Sidebar */}
        <div className="w-48 flex-shrink-0 bg-white/[0.02] border-r border-white/[0.06] p-4 flex flex-col">
          <h2 className="text-sm font-semibold text-white mb-1">Account</h2>
          <p className="text-xs text-neutral-600 mb-6">Manage your settings</p>

          <nav className="flex flex-col gap-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all ${
                  activeTab === tab.id
                    ? 'text-white bg-white/[0.06] border-l-2 border-l-[#e05929] -ml-[2px]'
                    : 'text-neutral-500 hover:text-neutral-300 hover:bg-white/[0.04]'
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 flex flex-col min-h-0">
          {/* Header */}
          <div className="flex items-center justify-between p-5 border-b border-white/[0.06]">
            <h3 className="text-base font-semibold text-white">
              {tabs.find((t) => t.id === activeTab)?.label}
            </h3>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] flex items-center justify-center transition-colors"
            >
              <X className="w-4 h-4 text-neutral-400" />
            </button>
          </div>

          {/* Scrollable body */}
          <div className="flex-1 overflow-y-auto p-5 space-y-6">
            {/* ═══ PROFILE TAB ═══ */}
            {activeTab === 'profile' && (
              <>
                {/* Avatar */}
                <div className="flex items-center gap-4">
                  <div className="relative">
                    <img
                      src={user.imageUrl}
                      alt="avatar"
                      className="w-16 h-16 rounded-full object-cover ring-2 ring-[#e05929]/30 ring-offset-2 ring-offset-black"
                    />
                    <button className="absolute -bottom-1 -right-1 w-7 h-7 rounded-full bg-[#e05929] flex items-center justify-center hover:bg-[#c94d23] transition-colors">
                      <Camera className="w-3.5 h-3.5 text-white" />
                    </button>
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">
                      {user.fullName || user.firstName || 'User'}
                    </p>
                    <p className="text-xs text-neutral-500">
                      {user.primaryEmailAddress?.emailAddress}
                    </p>
                  </div>
                </div>

                {/* Name */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="text-xs text-neutral-500 uppercase tracking-widest">Name</label>
                    {editingField !== 'name' && (
                      <button onClick={() => startEdit('name')} className="text-xs text-[#e05929] hover:text-[#ff7043] transition-colors flex items-center gap-1">
                        <Pencil className="w-3 h-3" /> Edit
                      </button>
                    )}
                  </div>
                  {editingField === 'name' ? (
                    <div className="space-y-2">
                      <div className="flex gap-2">
                        <input
                          value={firstName}
                          onChange={(e) => setFirstName(e.target.value)}
                          placeholder="First name"
                          className="flex-1 bg-white/[0.04] border border-white/[0.1] text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#e05929]/50"
                        />
                        <input
                          value={lastName}
                          onChange={(e) => setLastName(e.target.value)}
                          placeholder="Last name"
                          className="flex-1 bg-white/[0.04] border border-white/[0.1] text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#e05929]/50"
                        />
                      </div>
                      <div className="flex gap-2">
                        <button onClick={saveName} disabled={saving} className="px-3 py-1.5 rounded-lg bg-[#e05929] text-white text-xs font-medium hover:bg-[#c94d23] transition-colors disabled:opacity-50 flex items-center gap-1">
                          <Check className="w-3 h-3" /> Save
                        </button>
                        <button onClick={cancelEdit} className="px-3 py-1.5 rounded-lg text-neutral-400 hover:text-white text-xs transition-colors">
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-neutral-300">{user.fullName || '—'}</p>
                  )}
                </div>

                {/* Username */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="text-xs text-neutral-500 uppercase tracking-widest">Username</label>
                    {editingField !== 'username' && (
                      <button onClick={() => startEdit('username')} className="text-xs text-[#e05929] hover:text-[#ff7043] transition-colors flex items-center gap-1">
                        <Pencil className="w-3 h-3" /> Edit
                      </button>
                    )}
                  </div>
                  {editingField === 'username' ? (
                    <div className="space-y-2">
                      <input
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        placeholder="Username"
                        className="w-full bg-white/[0.04] border border-white/[0.1] text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#e05929]/50"
                      />
                      <div className="flex gap-2">
                        <button onClick={saveUsername} disabled={saving} className="px-3 py-1.5 rounded-lg bg-[#e05929] text-white text-xs font-medium hover:bg-[#c94d23] transition-colors disabled:opacity-50 flex items-center gap-1">
                          <Check className="w-3 h-3" /> Save
                        </button>
                        <button onClick={cancelEdit} className="px-3 py-1.5 rounded-lg text-neutral-400 hover:text-white text-xs transition-colors">
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-neutral-300">{user.username || '—'}</p>
                  )}
                </div>

                {/* Email */}
                <div className="space-y-1.5">
                  <label className="text-xs text-neutral-500 uppercase tracking-widest">Email</label>
                  <div className="flex items-center gap-2">
                    <p className="text-sm text-neutral-300">{user.primaryEmailAddress?.emailAddress}</p>
                    {user.primaryEmailAddress?.verification?.status === 'verified' && (
                      <span className="text-xs px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Verified</span>
                    )}
                  </div>
                </div>

                {/* Connected accounts */}
                <div className="space-y-1.5">
                  <label className="text-xs text-neutral-500 uppercase tracking-widest">Connected Accounts</label>
                  {user.externalAccounts && user.externalAccounts.length > 0 ? (
                    <div className="space-y-2">
                      {user.externalAccounts.map((account) => (
                        <div key={account.id} className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-white/[0.04] border border-white/[0.06]">
                          <div className="w-8 h-8 rounded-lg bg-white/[0.06] flex items-center justify-center">
                            <img src={account.imageUrl || ''} alt="" className="w-4 h-4 rounded-sm" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-white capitalize">{account.provider}</p>
                            <p className="text-xs text-neutral-500 truncate">{account.emailAddress}</p>
                          </div>
                          <span className="text-xs text-emerald-400">Connected</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-neutral-500">No connected accounts</p>
                  )}
                </div>
              </>
            )}

            {/* ═══ SECURITY TAB ═══ */}
            {activeTab === 'security' && (
              <>
                {/* Change password */}
                <div className="space-y-3">
                  <label className="text-xs text-neutral-500 uppercase tracking-widest">Password</label>
                  {!showPassword ? (
                    <button
                      onClick={() => setShowPassword(true)}
                      className="flex items-center gap-2.5 px-4 py-3 rounded-lg bg-white/[0.04] border border-white/[0.06] text-sm text-neutral-300 hover:bg-white/[0.06] hover:text-white transition-all w-full group"
                    >
                      <div className="w-8 h-8 rounded-lg bg-white/[0.04] border border-white/[0.06] flex items-center justify-center group-hover:border-white/[0.12] transition-colors">
                        <KeyRound className="w-4 h-4 text-neutral-500 group-hover:text-white transition-colors" />
                      </div>
                      Change password
                      <ChevronRight className="w-4 h-4 ml-auto text-neutral-600" />
                    </button>
                  ) : (
                    <div className="space-y-3 p-4 rounded-xl bg-white/[0.04] border border-white/[0.06]">
                      <div className="space-y-2">
                        <label className="text-xs text-neutral-500">Current password</label>
                        <div className="relative">
                          <input
                            type="password"
                            value={currentPassword}
                            onChange={(e) => setCurrentPassword(e.target.value)}
                            className="w-full bg-white/[0.04] border border-white/[0.1] text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#e05929]/50"
                          />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <label className="text-xs text-neutral-500">New password</label>
                        <input
                          type="password"
                          value={newPassword}
                          onChange={(e) => setNewPassword(e.target.value)}
                          placeholder="Min. 8 characters"
                          className="w-full bg-white/[0.04] border border-white/[0.1] text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#e05929]/50"
                        />
                      </div>
                      {passwordError && (
                        <p className="text-xs text-red-400">{passwordError}</p>
                      )}
                      {passwordSuccess && (
                        <p className="text-xs text-emerald-400">Password updated successfully</p>
                      )}
                      <div className="flex gap-2">
                        <button
                          onClick={handleChangePassword}
                          disabled={saving || !currentPassword || !newPassword}
                          className="px-3 py-1.5 rounded-lg bg-[#e05929] text-white text-xs font-medium hover:bg-[#c94d23] transition-colors disabled:opacity-50"
                        >
                          {saving ? 'Saving...' : 'Update password'}
                        </button>
                        <button
                          onClick={() => { setShowPassword(false); setPasswordError(''); setPasswordSuccess(false); setCurrentPassword(''); setNewPassword(''); }}
                          className="px-3 py-1.5 rounded-lg text-neutral-400 hover:text-white text-xs transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Active sessions */}
                <div className="space-y-3">
                  <label className="text-xs text-neutral-500 uppercase tracking-widest">Active Sessions</label>
                  {session && (
                    <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-white/[0.04] border border-white/[0.06]">
                      <div className="w-8 h-8 rounded-lg bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
                        <Monitor className="w-4 h-4 text-neutral-500" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-white">Current session</p>
                        <p className="text-xs text-neutral-500">
                          Last active: {new Date(session.lastActiveAt).toLocaleDateString('pl-PL', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </div>
                      <span className="text-xs px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        Active
                      </span>
                    </div>
                  )}
                </div>

                {/* Danger zone */}
                <div className="space-y-3">
                  <label className="text-xs text-neutral-500 uppercase tracking-widest">Danger Zone</label>
                  <div className="p-4 rounded-xl border border-red-500/20 bg-red-500/[0.04] space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-neutral-300">Sign out of all devices</p>
                        <p className="text-xs text-neutral-600">This will sign you out on all other devices</p>
                      </div>
                      <button
                        onClick={() => signOut()}
                        className="px-3 py-1.5 rounded-lg text-xs font-medium text-red-400 border border-red-500/20 hover:bg-red-500/10 transition-colors"
                      >
                        Sign out all
                      </button>
                    </div>
                  </div>
                </div>
              </>
            )}

            {activeTab === 'tier' && (
  <>
    <div className="space-y-4">
      <label className="text-xs text-neutral-500 uppercase tracking-widest">Current Tier</label>

      {isPro ? (
        /* Pro tier card */
        <div className="p-5 rounded-xl bg-emerald-500/[0.06] border border-emerald-500/20">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <span className="text-sm font-semibold text-emerald-400">Pro Plan</span>
          </div>
          <div className="space-y-2 mb-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-neutral-400">Daily searches</span>
              <span className="text-white">Unlimited</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-neutral-400">AI answers</span>
              <span className="text-white">Unlimited</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-neutral-400">Full judgment text</span>
              <span className="text-emerald-400">Included</span>
            </div>
          </div>
          <button
            onClick={handleManageBilling}
            disabled={saving}
            className="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg border border-white/[0.1] text-neutral-300 text-sm font-medium hover:bg-white/[0.06] transition-colors disabled:opacity-50"
          >
            Manage Billing
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      ) : (
        /* Free tier card */
        <div className="p-5 rounded-xl bg-[#e05929]/[0.06] border border-[#e05929]/20">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4 text-[#e05929]" />
            <span className="text-sm font-semibold text-[#e05929]">Free Plan</span>
          </div>
          <div className="space-y-2 mb-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-neutral-400">Daily searches</span>
              <span className="text-white">10 / day</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-neutral-400">AI answers</span>
              <span className="text-white">10 / day</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-neutral-400">Full judgment text</span>
              <span className="text-emerald-400">Included</span>
            </div>
          </div>
          <Link
            href="/pricing"
            onClick={onClose}
            className="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg bg-[#e05929] text-white text-sm font-medium hover:bg-[#c94d23] transition-colors"
          >
            Upgrade to Pro
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
      )}

      {/* Pro comparison — only show for free users */}
      {!isPro && (
        <div className="p-5 rounded-xl bg-white/[0.04] border border-white/[0.06]">
          <p className="text-sm font-semibold text-white mb-3">Pro includes</p>
          <div className="space-y-2.5">
            {[
              'Unlimited searches per day',
              'Unlimited AI answers',
              'Priority reranking',
              'Advanced filters (date, court type)',
              'Export results',
            ].map((feature) => (
              <div key={feature} className="flex items-center gap-2 text-sm">
                <Check className="w-3.5 h-3.5 text-[#e05929]" />
                <span className="text-neutral-300">{feature}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  </>
)}
          </div>
        </div>
      </div>
    </div>
  );
}