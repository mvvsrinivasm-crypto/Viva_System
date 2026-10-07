import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AppLayout from '../layouts/AppLayout';
import { LoadingState } from '../components/UI';

// Pages
import HomePage from '../pages/HomePage';
import LoginPage from '../pages/auth/LoginPage';
import RegisterPage from '../pages/auth/RegisterPage';

// Student Pages
import StudentDashboard from '../pages/student/StudentDashboard';
import StudentVivasPage from '../pages/student/StudentVivasPage';
import StudentVivaSession from '../pages/student/StudentVivaSession';
import StudentResultsPage from '../pages/student/StudentResultsPage';

// Faculty Pages
import FacultyDashboard from '../pages/faculty/FacultyDashboard';
import FacultyVivasPage from '../pages/faculty/FacultyVivasPage';
import FacultyQuestionsReview from '../pages/faculty/FacultyQuestionsReview';
import FacultyResultsPage from '../pages/faculty/FacultyResultsPage';
import FacultyStudentsPage from '../pages/faculty/FacultyStudentsPage';

// Admin Pages
import AdminDashboard from '../pages/admin/AdminDashboard';
import AdminUsersPage from '../pages/admin/AdminUsersPage';
import AdminResultsPage from '../pages/admin/AdminResultsPage';
import AdminAuditPage from '../pages/admin/AdminAuditPage';
import AdminViolationsPage from '../pages/admin/AdminViolationsPage';

// Route Guard component
const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, isAuthenticated, loading } = useAuth();

  if (loading) {
    return <LoadingState message="Checking session credentials..." />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user?.role)) {
    // If unauthorized, redirect to their home portal
    if (user?.role === 'ADMIN') return <Navigate to="/admin/dashboard" replace />;
    if (user?.role === 'FACULTY') return <Navigate to="/faculty/dashboard" replace />;
    return <Navigate to="/student/dashboard" replace />;
  }

  return children;
};

export const AppRoutes = () => {
  return (
    <Routes>
      {/* Public Pages wrapped in AppLayout */}
      <Route element={<AppLayout />}>
        <Route path="/" element={<HomePage />} />
      </Route>

      {/* Auth Pages (Clean standalone) */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Student Routes */}
      <Route
        path="/student"
        element={
          <ProtectedRoute allowedRoles={['STUDENT']}>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="dashboard" element={<StudentDashboard />} />
        <Route path="vivas" element={<StudentVivasPage />} />
        <Route path="viva/:id" element={<StudentVivaSession />} />
        <Route path="results" element={<StudentResultsPage />} />
      </Route>

      {/* Faculty Routes */}
      <Route
        path="/faculty"
        element={
          <ProtectedRoute allowedRoles={['FACULTY']}>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="dashboard" element={<FacultyDashboard />} />
        <Route path="vivas" element={<FacultyVivasPage />} />
        <Route path="vivas/:id/questions" element={<FacultyQuestionsReview />} />
        <Route path="vivas/:id/results" element={<FacultyResultsPage />} />
        <Route path="students" element={<FacultyStudentsPage />} />
        <Route path="results" element={<FacultyResultsPage />} />
      </Route>

      {/* Admin Routes */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="dashboard" element={<AdminDashboard />} />
        <Route path="users" element={<AdminUsersPage />} />
        <Route path="vivas" element={<FacultyVivasPage />} />
        <Route path="results" element={<AdminResultsPage />} />
        <Route path="audit" element={<AdminAuditPage />} />
        <Route path="mark-audit" element={<AdminAuditPage />} />
        <Route path="violations" element={<AdminViolationsPage />} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default AppRoutes;
