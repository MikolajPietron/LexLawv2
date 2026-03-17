'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useSignIn, useSignUp } from '@clerk/nextjs';
import {
  X,
  Mail,
  Lock,
  User,
  Eye,
  EyeOff,
  ArrowLeft,
  ChevronRight,
  AlertCircle,
} from 'lucide-react';

type AuthView = 'sign-in' | 'sign-up' | 'verify-email';

interface AuthModalProps {
  open: boolean;
  onClose: () => void;
  initialView?: 'sign-in' | 'sign-up';
}

export default function AuthModal({ open, onClose, initialView = 'sign-in' }: AuthModalProps) {
  const { signIn } = useSignIn();
  const { signUp } = useSignUp();

  const [view, setView] = useState<AuthView>(initialView);
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error, setError] = useState('');

  // Sign-in fields
  const [siEmail, setSiEmail] = useState('');
  const [siPassword, setSiPassword] = useState('');
  const [siShowPw, setSiShowPw] = useState(false);

  // Sign-up fields
  const [suEmail, setSuEmail] = useState('');
  const [suPassword, setSuPassword] = useState('');
  const [suUsername, setSuUsername] = useState('');
  const [suFirstName, setSuFirstName] = useState('');
  const [suLastName, setSuLastName] = useState('');
  const [suShowPw, setSuShowPw] = useState(false);

  // Verification
  const [code, setCode] = useState('');
  const codeRef = useRef<HTMLInputElement>(null);

  // Reset state when modal opens or view changes
  useEffect(() => {
    if (open) {
      setView(initialView);
      setError('');
      setLoading(false);
      setGoogleLoading(false);
    }
  }, [open, initialView]);

  if (!open || !signIn || !signUp) return null;

  const resetFields = () => {
    setSiEmail(''); setSiPassword(''); setSiShowPw(false);
    setSuEmail(''); setSuPassword(''); setSuUsername('');
    setSuFirstName(''); setSuLastName(''); setSuShowPw(false);
    setCode(''); setError('');
  };

  const switchView = (v: AuthView) => {
    resetFields();
    setView(v);
  };

  // ─── Sign In with Email/Password ───
  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      // Step 1: Create sign-in with identifier
      const createResult = await signIn.create({ identifier: siEmail });
      if (createResult.error) {
        setError(createResult.error.message || 'Sign in failed');
        setLoading(false);
        return;
      }

      // Step 2: Submit password
      const pwResult = await signIn.password({ password: siPassword });
      if (pwResult.error) {
        setError(pwResult.error.message || 'Invalid password');
        setLoading(false);
        return;
      }

      // Step 3: Finalize (sets active session)
      if (signIn.status === 'complete') {
        const finalResult = await signIn.finalize();
        if (finalResult.error) {
          setError(finalResult.error.message || 'Failed to complete sign in');
          setLoading(false);
          return;
        }
        onClose();
        resetFields();
      }
    } catch (err: any) {
      setError(err?.message || 'Sign in failed');
    }
    setLoading(false);
  };

  // ─── Sign In with Google ───
  const handleGoogleSignIn = async () => {
    setGoogleLoading(true);
    setError('');
    try {
      const result = await signIn.sso({
        strategy: 'oauth_google',
        redirectUrl: '/sso-callback',
        redirectCallbackUrl: '/',
      });
      if (result.error) {
        setError(result.error.message || 'Google sign in failed');
        setGoogleLoading(false);
      }
    } catch (err: any) {
      setError(err?.message || 'Google sign in failed');
      setGoogleLoading(false);
    }
  };

  // ─── Sign Up ───
  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      // Step 1: Create sign-up with email, username, name
      const createResult = await signUp.create({
        emailAddress: suEmail,
        username: suUsername || undefined,
        firstName: suFirstName || undefined,
        lastName: suLastName || undefined,
      });
      if (createResult.error) {
        setError(createResult.error.message || 'Sign up failed');
        setLoading(false);
        return;
      }

      // Step 2: Set password
      const pwResult = await signUp.password({
        password: suPassword,
        emailAddress: suEmail,
        username: suUsername || undefined,
      });
      if (pwResult.error) {
        setError(pwResult.error.message || 'Password error');
        setLoading(false);
        return;
      }

      // Step 3: Send email verification code
      const verifyResult = await signUp.verifications.sendEmailCode();
      if (verifyResult.error) {
        setError(verifyResult.error.message || 'Failed to send verification code');
        setLoading(false);
        return;
      }

      setView('verify-email');
    } catch (err: any) {
      setError(err?.message || 'Sign up failed');
    }
    setLoading(false);
  };

  // ─── Verify Email ───
  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const result = await signUp.verifications.verifyEmailCode({ code });
      if (result.error) {
        setError(result.error.message || 'Verification failed');
        setLoading(false);
        return;
      }

      if (signUp.status === 'complete') {
        const finalResult = await signUp.finalize();
        if (finalResult.error) {
          setError(finalResult.error.message || 'Failed to complete sign up');
          setLoading(false);
          return;
        }
        onClose();
        resetFields();
      }
    } catch (err: any) {
      setError(err?.message || 'Verification failed');
    }
    setLoading(false);
  };

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
        className="relative w-full max-w-md rounded-2xl bg-black/80 backdrop-blur-xl border border-white/[0.08] overflow-hidden shadow-2xl shadow-black/60"
        style={{ animation: 'modalDrawerUp 0.5s cubic-bezier(0.16, 1, 0.3, 1)' }}
      >
        {/* Orange glow at top */}
        <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-[#e05929] to-transparent" />

        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-10 w-8 h-8 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] flex items-center justify-center transition-colors"
        >
          <X className="w-4 h-4 text-neutral-400" />
        </button>

        <div className="p-8">
          {/* ═══ SIGN IN ═══ */}
          {view === 'sign-in' && (
            <>
              <div className="mb-8">
                <h2 className="text-2xl font-bold text-white tracking-tight mb-1">Welcome back</h2>
                <p className="text-sm text-neutral-500">Sign in to your account to continue</p>
              </div>

              {/* Google button */}
              <button
                onClick={handleGoogleSignIn}
                disabled={googleLoading}
                className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-xl bg-white/[0.06] border border-white/[0.1] text-neutral-300 text-sm font-medium hover:bg-white/[0.1] transition-all duration-200 disabled:opacity-50 mb-6"
              >
                {googleLoading ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    <svg className="w-5 h-5" viewBox="0 0 24 24">
                      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
                      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                    </svg>
                    Continue with Google
                  </>
                )}
              </button>

              {/* Divider */}
              <div className="flex items-center gap-4 mb-6">
                <div className="flex-1 h-[1px] bg-white/[0.08]" />
                <span className="text-xs text-neutral-600 uppercase tracking-wider">or</span>
                <div className="flex-1 h-[1px] bg-white/[0.08]" />
              </div>

              {/* Email/Password form */}
              <form onSubmit={handleSignIn} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs text-neutral-500 font-medium">Email</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-600" />
                    <input
                      type="email"
                      value={siEmail}
                      onChange={(e) => setSiEmail(e.target.value)}
                      placeholder="you@example.com"
                      required
                      className="w-full bg-white/[0.04] border border-white/[0.1] text-white rounded-xl pl-10 pr-4 py-3 text-sm placeholder:text-neutral-600 focus:outline-none focus:border-[#e05929]/50 focus:ring-1 focus:ring-[#e05929]/20 transition-colors"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs text-neutral-500 font-medium">Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-600" />
                    <input
                      type={siShowPw ? 'text' : 'password'}
                      value={siPassword}
                      onChange={(e) => setSiPassword(e.target.value)}
                      placeholder="Enter your password"
                      required
                      className="w-full bg-white/[0.04] border border-white/[0.1] text-white rounded-xl pl-10 pr-12 py-3 text-sm placeholder:text-neutral-600 focus:outline-none focus:border-[#e05929]/50 focus:ring-1 focus:ring-[#e05929]/20 transition-colors"
                    />
                    <button
                      type="button"
                      onClick={() => setSiShowPw(!siShowPw)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-600 hover:text-neutral-400 transition-colors"
                    >
                      {siShowPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {error && (
                  <div className="flex items-start gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
                    <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3 rounded-xl bg-[#e05929] hover:bg-[#ff6b3d] text-white font-semibold text-sm shadow-lg shadow-[#e05929]/25 transition-all duration-300 hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 disabled:hover:translate-y-0 flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>
                      Sign In
                      <ChevronRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>

              <p className="mt-6 text-center text-sm text-neutral-500">
                Don&apos;t have an account?{' '}
                <button onClick={() => switchView('sign-up')} className="text-[#e05929] hover:text-[#ff7043] font-medium transition-colors">
                  Sign Up
                </button>
              </p>
            </>
          )}

          {/* ═══ SIGN UP ═══ */}
          {view === 'sign-up' && (
            <>
              <div className="mb-8">
                <h2 className="text-2xl font-bold text-white tracking-tight mb-1">Create an account</h2>
                <p className="text-sm text-neutral-500">Get started with Lexara</p>
              </div>

              <form onSubmit={handleSignUp} className="space-y-4">
                {/* Name row */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <label className="text-xs text-neutral-500 font-medium">
                      First name <span className="text-neutral-700">Optional</span>
                    </label>
                    <input
                      type="text"
                      value={suFirstName}
                      onChange={(e) => setSuFirstName(e.target.value)}
                      placeholder="First name"
                      className="w-full bg-white/[0.04] border border-white/[0.1] text-white rounded-xl px-4 py-3 text-sm placeholder:text-neutral-600 focus:outline-none focus:border-[#e05929]/50 focus:ring-1 focus:ring-[#e05929]/20 transition-colors"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs text-neutral-500 font-medium">
                      Last name <span className="text-neutral-700">Optional</span>
                    </label>
                    <input
                      type="text"
                      value={suLastName}
                      onChange={(e) => setSuLastName(e.target.value)}
                      placeholder="Last name"
                      className="w-full bg-white/[0.04] border border-white/[0.1] text-white rounded-xl px-4 py-3 text-sm placeholder:text-neutral-600 focus:outline-none focus:border-[#e05929]/50 focus:ring-1 focus:ring-[#e05929]/20 transition-colors"
                    />
                  </div>
                </div>

                {/* Username */}
                <div className="space-y-1.5">
                  <label className="text-xs text-neutral-500 font-medium">Username</label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-600" />
                    <input
                      type="text"
                      value={suUsername}
                      onChange={(e) => setSuUsername(e.target.value)}
                      placeholder="Choose a username"
                      className="w-full bg-white/[0.04] border border-white/[0.1] text-white rounded-xl pl-10 pr-4 py-3 text-sm placeholder:text-neutral-600 focus:outline-none focus:border-[#e05929]/50 focus:ring-1 focus:ring-[#e05929]/20 transition-colors"
                    />
                  </div>
                </div>

                {/* Email */}
                <div className="space-y-1.5">
                  <label className="text-xs text-neutral-500 font-medium">Email</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-600" />
                    <input
                      type="email"
                      value={suEmail}
                      onChange={(e) => setSuEmail(e.target.value)}
                      placeholder="you@example.com"
                      required
                      className="w-full bg-white/[0.04] border border-white/[0.1] text-white rounded-xl pl-10 pr-4 py-3 text-sm placeholder:text-neutral-600 focus:outline-none focus:border-[#e05929]/50 focus:ring-1 focus:ring-[#e05929]/20 transition-colors"
                    />
                  </div>
                </div>

                {/* Password */}
                <div className="space-y-1.5">
                  <label className="text-xs text-neutral-500 font-medium">Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-600" />
                    <input
                      type={suShowPw ? 'text' : 'password'}
                      value={suPassword}
                      onChange={(e) => setSuPassword(e.target.value)}
                      placeholder="Min. 8 characters"
                      required
                      className="w-full bg-white/[0.04] border border-white/[0.1] text-white rounded-xl pl-10 pr-12 py-3 text-sm placeholder:text-neutral-600 focus:outline-none focus:border-[#e05929]/50 focus:ring-1 focus:ring-[#e05929]/20 transition-colors"
                    />
                    <button
                      type="button"
                      onClick={() => setSuShowPw(!suShowPw)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-600 hover:text-neutral-400 transition-colors"
                    >
                      {suShowPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {error && (
                  <div className="flex items-start gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
                    <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3 rounded-xl bg-[#e05929] hover:bg-[#ff6b3d] text-white font-semibold text-sm shadow-lg shadow-[#e05929]/25 transition-all duration-300 hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 disabled:hover:translate-y-0 flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>
                      Create Account
                      <ChevronRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>

              <p className="mt-6 text-center text-sm text-neutral-500">
                Already have an account?{' '}
                <button onClick={() => switchView('sign-in')} className="text-[#e05929] hover:text-[#ff7043] font-medium transition-colors">
                  Sign In
                </button>
              </p>
            </>
          )}

          {/* ═══ VERIFY EMAIL ═══ */}
          {view === 'verify-email' && (
            <>
              <button
                onClick={() => switchView('sign-up')}
                className="flex items-center gap-1.5 text-sm text-neutral-500 hover:text-white transition-colors mb-6"
              >
                <ArrowLeft className="w-4 h-4" />
                Back
              </button>

              <div className="mb-8 text-center">
                <div className="w-16 h-16 rounded-2xl bg-[#e05929]/10 border border-[#e05929]/20 flex items-center justify-center mx-auto mb-5">
                  <Mail className="w-7 h-7 text-[#e05929]" />
                </div>
                <h2 className="text-2xl font-bold text-white tracking-tight mb-1">Check your email</h2>
                <p className="text-sm text-neutral-500">
                  We sent a verification code to<br />
                  <span className="text-neutral-300">{suEmail}</span>
                </p>
              </div>

              <form onSubmit={handleVerify} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs text-neutral-500 font-medium">Verification code</label>
                  <input
                    ref={codeRef}
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="Enter 6-digit code"
                    required
                    className="w-full bg-white/[0.04] border border-white/[0.1] text-white rounded-xl px-4 py-3 text-sm text-center tracking-[0.3em] font-mono placeholder:text-neutral-600 placeholder:tracking-normal placeholder:font-sans focus:outline-none focus:border-[#e05929]/50 focus:ring-1 focus:ring-[#e05929]/20 transition-colors"
                  />
                </div>

                {error && (
                  <div className="flex items-start gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
                    <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading || code.length < 6}
                  className="w-full py-3 rounded-xl bg-[#e05929] hover:bg-[#ff6b3d] text-white font-semibold text-sm shadow-lg shadow-[#e05929]/25 transition-all duration-300 hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 disabled:hover:translate-y-0 flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    'Verify & Continue'
                  )}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}