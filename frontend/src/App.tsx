import { Toaster } from "./components/ui/toaster";
import { Toaster as Sonner } from "./components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
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

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout><Dashboard /></Layout>} />
          <Route path="/file-upload" element={<Layout><FileUpload /></Layout>} />
          <Route path="/view-status" element={<Layout><ViewStatus /></Layout>} />
          <Route path="/recon" element={<Layout><Recon /></Layout>} />
          <Route path="/unmatched" element={<Layout><Unmatched /></Layout>} />
          <Route path="/force-match" element={<Layout><ForceMatch /></Layout>} />
          <Route path="/auto-match" element={<Layout><AutoMatch /></Layout>} />
          <Route path="/rollback" element={<Layout><Rollback /></Layout>} />
          <Route path="/enquiry" element={<Layout><Enquiry /></Layout>} />
          <Route path="/reports" element={<Layout><Reports /></Layout>} />
          <Route path="/audit" element={<Layout><Audit /></Layout>} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
