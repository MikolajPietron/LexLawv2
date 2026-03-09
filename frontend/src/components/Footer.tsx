import React from 'react'
import LogoHeader from '../../public/logo.svg'
import Image from 'next/image'
import Link from 'next/link'

const Footer = () => {
  return (
    <footer className='bg-black/90 backdrop-blur-md border-t border-white/[0.06]'>
      <div className='max-w-7xl mx-auto px-8 py-10'>
        <div className='flex flex-col md:flex-row items-start justify-between gap-10'>

          {/* Brand */}
          <div className='flex flex-col gap-3'>
            <Image src={LogoHeader} alt='logo' className='h-8 w-auto' />
            <p className='text-sm text-neutral-500 max-w-[260px] leading-relaxed'>
              Inteligentne wyszukiwanie orzeczeń sądowych wspierane przez AI.
            </p>
          </div>

          {/* Navigation */}
          <div className='flex flex-col gap-3'>
            <h4 className='text-xs font-semibold uppercase tracking-widest text-neutral-500'>Nawigacja</h4>
            <nav className='flex flex-col gap-2'>
              <Link href="/home" className='text-sm text-neutral-400 hover:text-white transition-colors'>Home</Link>
              <Link href="/about" className='text-sm text-neutral-400 hover:text-white transition-colors'>About</Link>
              <Link href="/contact" className='text-sm text-neutral-400 hover:text-white transition-colors'>Contact</Link>
              <Link href="/home" className='text-sm text-neutral-400 hover:text-white transition-colors'>Pricing</Link>
            </nav>
          </div>

          {/* Legal */}
          <div className='flex flex-col gap-3'>
            <h4 className='text-xs font-semibold uppercase tracking-widest text-neutral-500'>Informacje</h4>
            <nav className='flex flex-col gap-2'>
              <Link href="/privacy" className='text-sm text-neutral-400 hover:text-white transition-colors'>Polityka prywatności</Link>
              <Link href="/terms" className='text-sm text-neutral-400 hover:text-white transition-colors'>Regulamin</Link>
            </nav>
          </div>

          {/* Contact / CTA */}
          <div className='flex flex-col gap-3'>
            <h4 className='text-xs font-semibold uppercase tracking-widest text-neutral-500'>Kontakt</h4>
            <a href="mailto:kontakt@example.com" className='text-sm text-neutral-400 hover:text-white transition-colors'>kontakt@example.com</a>
            <Link href="/contact" className='text-sm bg-[#e05929] text-white px-4 py-1.5 rounded-lg font-medium hover:text-black duration-500 hover:bg-neutral-200 transition-colors text-center mt-1'>
              Napisz do nas
            </Link>
          </div>

        </div>
      </div>

      {/* Bottom bar */}
      <div className='border-t border-white/[0.06] px-8 py-4'>
        <p className='text-xs text-neutral-500 text-center'>&copy; {new Date().getFullYear()} All rights reserved.</p>
      </div>
    </footer>
  )
}

export default Footer