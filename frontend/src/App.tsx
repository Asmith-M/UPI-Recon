import { useState, useEffect } from "react";
import { Toaster } from "./components/ui/toaster";
import { Toaster as Sonner } from "./components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import FileUpload from "./pages/FileUpload";
import ViewStatus from "./pages/ViewStatus";
import Recon from "./pages/Recon";
import Unmatched from "./pages/Unmatched";
import Reports from "./pages/Reports";
import Enquiry from "./pages/Enquiry";
import ForceMatch from "./pages/ForceMatch";
import AutoMatch from "./pages/AutoMatch";
import Rollback from "./pages/Rollback";
import Audit from "./pages/Audit";
import NotFound from "./pages/NotFound";
import Login from "./pages/Login";
import WelcomeDialog from "./components/WelcomeDialog";

const queryClient = new QueryClient();

// Protected Route component
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
};

// App Routes component that uses auth context
const AppRoutes = () => {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/" element={<ProtectedRoute><Layout><Dashboard /></Layout></ProtectedRoute>} />
      <Route path="/file-upload" element={<ProtectedRoute><Layout><FileUpload /></Layout></ProtectedRoute>} />
      <Route path="/view-status" element={<ProtectedRoute><Layout><ViewStatus /></Layout></ProtectedRoute>} />
      <Route path="/recon" element={<ProtectedRoute><Layout><Recon /></Layout></ProtectedRoute>} />
      <Route path="/unmatched" element={<ProtectedRoute><Layout><Unmatched /></Layout></ProtectedRoute>} />
      <Route path="/force-match" element={<ProtectedRoute><Layout><ForceMatch /></Layout></ProtectedRoute>} />
      <Route path="/auto-match" element={<ProtectedRoute><Layout><AutoMatch /></Layout></ProtectedRoute>} />
      <Route path="/rollback" element={<ProtectedRoute><Layout><Rollback /></Layout></ProtectedRoute>} />
      <Route path="/enquiry" element={<ProtectedRoute><Layout><Enquiry /></Layout></ProtectedRoute>} />
      <Route path="/reports" element={<ProtectedRoute><Layout><Reports /></Layout></ProtectedRoute>} />
      <Route path="/audit" element={<ProtectedRoute><Layout><Audit /></Layout></ProtectedRoute>} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </TooltipProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;
