import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/UI';
import { Lock, Mail, AlertCircle, Shield, BookOpen, GraduationCap, Eye, EyeOff } from 'lucide-react';

export const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const user = await login(email, password);
      if (user.role === 'ADMIN') {
        navigate('/admin/dashboard');
      } else if (user.role === 'FACULTY') {
        navigate('/faculty/dashboard');
      } else {
        navigate('/student/dashboard');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Invalid credentials. Please verify your email and password.');
    } finally {
      setLoading(false);
    }
  };



  return (
    <div className="min-h-screen bg-gradient-to-b from-[#dfedf8] via-[#e9f3fa] to-[#f4f9fd] flex flex-col justify-center items-center py-10 px-4 sm:px-6 lg:px-8 font-sans">
      {/* Centered White Institutional Login Card */}
      <div className="w-full max-w-[440px] bg-white rounded-2xl shadow-xl shadow-sky-950/5 border border-sky-100 p-7 sm:p-9 transition-all">
        {/* KARE Institutional Logo (Exactly ONCE on the page) */}
        <div className="flex justify-center mb-4">
          <img
            src="/kare_logo.png"
            alt="Kalasalingam Academy of Research and Education"
            className="h-12 sm:h-14 w-auto max-w-[280px] object-contain"
          />
        </div>

        {/* Portal Titles with strict academic hierarchy */}
        <div className="text-center mb-6">
          <h1 className="text-xl sm:text-2xl font-bold text-slate-800 tracking-tight">
            Viva Evaluation System
          </h1>
          <p className="mt-1 text-xs sm:text-[13px] text-slate-500 font-medium">
            Kalasalingam Academy of Research and Education
          </p>
        </div>

        {/* Authentication Form */}
        <form className="space-y-4" onSubmit={handleSubmit}>
          {error && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              Institutional Email
            </label>
            <div className="relative rounded-lg shadow-2xs">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                <Mail className="h-4 w-4" />
              </div>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@klu.ac.in"
                className="block w-full pl-9 pr-3 py-2.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500/20 focus:border-sky-600 bg-white placeholder:text-slate-400 text-slate-800 transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              Password
            </label>
            <div className="relative rounded-lg shadow-2xs">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                <Lock className="h-4 w-4" />
              </div>
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="block w-full pl-9 pr-10 py-2.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500/20 focus:border-sky-600 bg-white placeholder:text-slate-400 text-slate-800 transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 focus:outline-hidden"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <Button
            type="submit"
            variant="primary"
            size="md"
            loading={loading}
            className="w-full mt-2 py-2.5 bg-[#0284c7] hover:bg-[#0369a1] text-white font-medium rounded-lg shadow-xs transition-colors"
          >
            Sign In to Portal
          </Button>
        </form>



        {/* Registration Section */}
        <div className="mt-5 text-center">
          <p className="text-xs text-slate-500">
            Don&apos;t have an account?{' '}
            <Link to="/register" className="font-semibold text-sky-600 hover:text-sky-700">
              Register as Student or Faculty
            </Link>
          </p>
        </div>
      </div>

      {/* Institutional Accreditation Note */}
      <p className="mt-6 text-center text-xs text-slate-400">
        (Deemed to be University under sec. 3 of UGC Act 1956) • NAAC &quot;A++&quot; Accredited
      </p>
    </div>
  );
};

export default LoginPage;
