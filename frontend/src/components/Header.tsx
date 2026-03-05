import React from 'react'
import LogoHeader from '../../public/logo.svg'
import Image from 'next/image'
import Link from 'next/link'
import { Show, SignInButton, SignUpButton, UserButton } from '@clerk/nextjs'

const Header = () => {
  return (
    <header className='fixed top-0 left-0 right-0 z-50 flex items-center justify-between h-[60px] px-8 bg-black/90 backdrop-blur-md border-b border-white/[0.06]'>
      <Image src={LogoHeader} alt='logo' className='h-8 w-auto' />
      <nav className='flex items-center gap-8'>
        <Link href="/home" className='text-sm text-neutral-400 hover:text-white transition-colors'>Home</Link>
        <Link href="/about" className='text-sm text-neutral-400 hover:text-white transition-colors'>About</Link>
        <Link href="/contact" className='text-sm text-neutral-400 hover:text-white transition-colors'>Contact</Link>
        <Link href="/home" className='text-sm text-neutral-400 hover:text-white transition-colors'>Pricing</Link>
      </nav>
      <div className='flex items-center gap-3'>
        <Show when="signed-out">
          <SignInButton>
            <button className='text-sm text-neutral-400 hover:text-white px-4 py-1.5 transition-colors cursor-pointer'>Sign In</button>
          </SignInButton>
          <SignUpButton>
            <button className='text-sm bg-[#8b2c8b] text-white px-4 py-1.5 rounded-lg font-medium hover:bg-neutral-200 cursor-pointer transition-colors'>Sign Up</button>
          </SignUpButton>
        </Show>
        <Show when="signed-in">
          <UserButton />
        </Show>
      </div>
    </header>
  )
}

export default Header