'use client';

import React, { useState, useRef, useEffect } from 'react'
import LogoHeader from '../../public/logo.svg'
import Image from 'next/image'
import Link from 'next/link'
import { useUser, useClerk } from '@clerk/nextjs'
import { LogOut, Settings, Sparkles, ChevronRight, Menu, X } from 'lucide-react'
import ProfileModal from './ProfileModal'
import { useAuthModal } from './AuthContext'

const Header = () => {
  const { isSignedIn, user } = useUser();
  const { signOut } = useClerk();
  const { openSignIn, openSignUp } = useAuthModal();
  const [menuOpen, setMenuOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const tier = (user?.publicMetadata as any)?.tier || 'free';
  const isPro = tier === 'pro';

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  // Close mobile menu on resize to desktop
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 768) setMobileOpen(false);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const navLinks = (
    <>
      <Link href="/" onClick={() => setMobileOpen(false)} className='text-sm text-neutral-400 hover:text-white transition-colors'>Home</Link>
      <Link href="/about" onClick={() => setMobileOpen(false)} className='text-sm text-neutral-400 hover:text-white transition-colors'>About</Link>
      <Link href="#contact" onClick={() => setMobileOpen(false)} className='text-sm text-neutral-400 hover:text-white transition-colors'>Contact</Link>
      <Link href="/pricing" onClick={() => setMobileOpen(false)} className='text-sm text-neutral-400 hover:text-white transition-colors'>Pricing</Link>
    </>
  );

  return (
    <>
      <header className='fixed top-0 left-0 right-0 z-50 h-[60px] bg-black/90 backdrop-blur-md border-b border-white/[0.06]'>
        {/* Desktop: 3-column grid so nav is always centered */}
        <div className='hidden md:grid grid-cols-[1fr_auto_1fr] items-center h-full px-8'>
          {/* Left — Logo */}
          <div className='flex items-center'>
            <Image src={LogoHeader} alt='logo' className='h-8 w-auto' />
          </div>

          {/* Center — Nav (always centered regardless of left/right width) */}
          <nav className='flex items-center gap-8'>
            {navLinks}
          </nav>

          {/* Right — Auth / Avatar */}
          <div className='flex items-center justify-end gap-3'>
            {!isSignedIn ? (
              <>
                <button
                  onClick={openSignIn}
                  className='text-sm text-neutral-400 hover:text-white px-4 py-1.5 transition-colors cursor-pointer'
                >
                  Sign In
                </button>
                <button
                  onClick={openSignUp}
                  className='text-sm bg-[#e05929] text-white px-4 py-1.5 rounded-lg font-medium hover:text-black duration-500 hover:bg-neutral-200 cursor-pointer transition-colors'
                >
                  Sign Up
                </button>
              </>
            ) : (
              <div className='relative' ref={menuRef}>
                <button
                  onClick={() => setMenuOpen(!menuOpen)}
                  className={`relative w-9 h-9 rounded-full cursor-pointer transition-all duration-300 ${
                    menuOpen
                      ? 'ring-2 ring-[#e05929] ring-offset-2 ring-offset-black'
                      : 'ring-1 ring-white/[0.1] hover:ring-[#e05929]/60'
                  }`}
                >
                  <img
                    src={user?.imageUrl}
                    alt='avatar'
                    className='w-full h-full rounded-full object-cover'
                  />
                  <span className='absolute bottom-0 right-0 w-2.5 h-2.5 bg-emerald-500 rounded-full border-2 border-black' />
                </button>

                <div
                  className={`absolute right-0 mt-3 w-72 rounded-2xl bg-black/95 backdrop-blur-2xl border border-white/[0.08] shadow-2xl shadow-black/60 overflow-hidden transition-all duration-300 origin-top-right ${
                    menuOpen
                      ? 'opacity-100 scale-100 translate-y-0'
                      : 'opacity-0 scale-95 -translate-y-2 pointer-events-none'
                  }`}
                >
                  <div className='absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-[#e05929] to-transparent' />
                  <div className='p-4'>
                    <div className='flex items-center gap-3'>
                      <div className='relative flex-shrink-0'>
                        <img src={user?.imageUrl} alt='avatar' className='w-11 h-11 rounded-full object-cover ring-1 ring-white/[0.1]' />
                      </div>
                      <div className='flex-1 min-w-0'>
                        <p className='text-sm font-semibold text-white truncate'>{user?.fullName || user?.firstName || 'User'}</p>
                        <p className='text-xs text-neutral-500 truncate'>{user?.primaryEmailAddress?.emailAddress}</p>
                      </div>
                    </div>
                    <div className={`mt-3 flex items-center gap-2 px-3 py-2 rounded-lg ${isPro ? 'bg-emerald-500/10 border border-emerald-500/20' : 'bg-[#e05929]/10 border border-[#e05929]/20'}`}>
                      <Sparkles className={`w-3.5 h-3.5 ${isPro ? 'text-emerald-400' : 'text-[#e05929]'}`} />
                      <span className={`text-xs font-medium ${isPro ? 'text-emerald-400' : 'text-[#e05929]'}`}>{isPro ? 'Pro Plan' : 'Free Plan'}</span>
                      {!isPro && (
                        <Link href='/pricing' onClick={() => setMenuOpen(false)} className='ml-auto text-xs text-[#e05929] hover:text-[#ff7043] transition-colors flex items-center gap-0.5'>
                          Upgrade<ChevronRight className='w-3 h-3' />
                        </Link>
                      )}
                    </div>
                  </div>
                  <div className='h-[1px] bg-white/[0.06]' />
                  <div className='p-2'>
                    <button onClick={() => { setProfileOpen(true); setMenuOpen(false); }} className='w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-neutral-300 hover:bg-white/[0.06] hover:text-white transition-all group'>
                      <div className='w-8 h-8 rounded-lg bg-white/[0.04] border border-white/[0.06] flex items-center justify-center group-hover:border-white/[0.12] transition-colors'>
                        <Settings className='w-4 h-4 text-neutral-500 group-hover:text-white transition-colors' />
                      </div>
                      <div className='text-left'>
                        <p className='text-sm'>Manage Account</p>
                        <p className='text-xs text-neutral-600'>Profile, security & preferences</p>
                      </div>
                    </button>
                  </div>
                  <div className='h-[1px] bg-white/[0.06]' />
                  <div className='p-2'>
                    <button onClick={() => { signOut(); setMenuOpen(false); }} className='w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-neutral-400 hover:bg-red-500/10 hover:text-red-400 transition-all group'>
                      <div className='w-8 h-8 rounded-lg bg-white/[0.04] border border-white/[0.06] flex items-center justify-center group-hover:border-red-500/20 transition-colors'>
                        <LogOut className='w-4 h-4 text-neutral-500 group-hover:text-red-400 transition-colors' />
                      </div>
                      Sign Out
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Mobile: logo + hamburger */}
        <div className='flex md:hidden items-center justify-between h-full px-5'>
          <Image src={LogoHeader} alt='logo' className='h-7 w-auto' />
          <div className='flex items-center gap-3'>
            {isSignedIn && (
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className='relative w-8 h-8 rounded-full ring-1 ring-white/[0.1]'
              >
                <img src={user?.imageUrl} alt='avatar' className='w-full h-full rounded-full object-cover' />
              </button>
            )}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className='w-9 h-9 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] flex items-center justify-center transition-colors'
            >
              {mobileOpen ? <X className='w-5 h-5 text-neutral-400' /> : <Menu className='w-5 h-5 text-neutral-400' />}
            </button>
          </div>
        </div>
      </header>

      {/* Mobile menu overlay */}
      {mobileOpen && (
        <div className='fixed inset-0 z-40 md:hidden'>
          <div className='absolute inset-0 bg-black/80 backdrop-blur-sm' onClick={() => setMobileOpen(false)} />
          <div
            className='absolute top-[60px] left-0 right-0 bg-black/95 backdrop-blur-xl border-b border-white/[0.08] p-6 space-y-6'
            style={{ animation: 'modalOverlayIn 0.2s ease-out' }}
          >
            <nav className='flex flex-col gap-4'>
              {navLinks}
            </nav>
            <div className='h-[1px] bg-white/[0.06]' />
            {!isSignedIn ? (
              <div className='flex flex-col gap-3'>
                <button
                  onClick={() => { openSignIn(); setMobileOpen(false); }}
                  className='w-full py-3 rounded-xl border border-white/[0.1] bg-white/[0.04] text-sm text-neutral-300 font-medium hover:bg-white/[0.08] transition-colors'
                >
                  Sign In
                </button>
                <button
                  onClick={() => { openSignUp(); setMobileOpen(false); }}
                  className='w-full py-3 rounded-xl bg-[#e05929] hover:bg-[#ff6b3d] text-white text-sm font-semibold shadow-lg shadow-[#e05929]/25 transition-all'
                >
                  Sign Up
                </button>
              </div>
            ) : (
              <div className='flex flex-col gap-2'>
                <div className='flex items-center gap-3 px-2 py-2'>
                  <img src={user?.imageUrl} alt='avatar' className='w-10 h-10 rounded-full object-cover ring-1 ring-white/[0.1]' />
                  <div className='min-w-0'>
                    <p className='text-sm font-semibold text-white truncate'>{user?.fullName || user?.firstName || 'User'}</p>
                    <p className='text-xs text-neutral-500 truncate'>{user?.primaryEmailAddress?.emailAddress}</p>
                  </div>
                </div>
                <button
                  onClick={() => { setProfileOpen(true); setMobileOpen(false); }}
                  className='w-full flex items-center gap-3 px-3 py-3 rounded-lg text-sm text-neutral-300 hover:bg-white/[0.06] transition-colors'
                >
                  <Settings className='w-4 h-4 text-neutral-500' />
                  Manage Account
                </button>
                <button
                  onClick={() => { signOut(); setMobileOpen(false); }}
                  className='w-full flex items-center gap-3 px-3 py-3 rounded-lg text-sm text-red-400 hover:bg-red-500/10 transition-colors'
                >
                  <LogOut className='w-4 h-4' />
                  Sign Out
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      <ProfileModal open={profileOpen} onClose={() => setProfileOpen(false)} />
    </>
  )
}

export default Header