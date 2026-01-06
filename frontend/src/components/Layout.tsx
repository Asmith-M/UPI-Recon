import { ReactNode, useState, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useDate } from "../contexts/DateContext";
import { cn } from "../lib/utils";
import {
  LayoutDashboard,
  Upload,
  Eye,
  BarChart3,
  AlertCircle,
  GitMerge,
  PlayCircle,
  RotateCcw,
  HelpCircle,
  FileText,
  PanelLeftClose,
  PanelLeft,
  LogOut
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "../components/ui/tooltip";
import DateFilter from "./DateFilter";
import nstechxLogo from "../assets/nstechxbg.png";
import verifAiLogo from "../assets/verif_ai.png";

interface LayoutProps {
  children: ReactNode;
}

const menuItems = [
  { path: "/", label: "Dashboard", icon: LayoutDashboard },
  { path: "/file-upload", label: "File Upload", icon: Upload },
  { path: "/view-status", label: "View Upload Status", icon: Eye },
  { path: "/recon", label: "Recon Dashboard", icon: BarChart3 },
  { path: "/unmatched", label: "Unmatched Dashboard", icon: AlertCircle },
  { path: "/force-match", label: "Force - Match", icon: GitMerge },
  { path: "/auto-match", label: "Auto-Match", icon: PlayCircle },
  { path: "/rollback", label: "Roll-Back", icon: RotateCcw },
  { path: "/enquiry", label: "Enquiry", icon: HelpCircle },
  { path: "/reports", label: "Reports", icon: FileText },
];

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout, user } = useAuth();
  const { dateFrom, dateTo, setDateRange } = useDate();
  const [isCollapsed, setIsCollapsed] = useState(true); // Start collapsed

  // Load saved state from localStorage
  useEffect(() => {
    const saved = localStorage.getItem("sidebar-collapsed");
    if (saved !== null) {
      setIsCollapsed(saved === "true");
    }
  }, []);

  // Save state to localStorage
  const toggleSidebar = () => {
    const newState = !isCollapsed;
    setIsCollapsed(newState);
    localStorage.setItem("sidebar-collapsed", String(newState));
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="flex min-h-screen w-full bg-background">
      {/* Sidebar */}
      <aside 
        className={cn(
          "bg-sidebar border-r border-sidebar-border shadow-xl transition-all duration-300 ease-in-out flex flex-col",
          isCollapsed ? "w-16" : "w-64"
        )}
      >
        <div className="p-3 flex-1 flex flex-col">
          {/* Logo Section */}
          <div className={cn(
            "mb-4 pb-4 border-b border-sidebar-border flex justify-center",
            isCollapsed ? "px-2" : "px-4"
          )}>
            <img 
              src={nstechxLogo} 
              alt="NStechX" 
              className={cn(
                "object-contain rounded",
                isCollapsed ? "h-16 w-16" : "h-24 w-24"
              )}
            />
          </div>

          {/* Toggle Button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className="mb-4 self-end text-sidebar-foreground hover:bg-sidebar-accent"
          >
            {isCollapsed ? (
              <PanelLeft className="w-5 h-5" />
            ) : (
              <PanelLeftClose className="w-5 h-5" />
            )}
          </Button>

          {/* User Info */}
          <div className={cn(
            "flex items-center gap-3 mb-6 pb-4 border-b border-sidebar-border",
            isCollapsed && "justify-center"
          )}>
            <div className="w-10 h-10 rounded-full bg-sidebar-primary flex items-center justify-center flex-shrink-0">
              <span className="text-sidebar-primary-foreground font-semibold">
                {user?.username?.[0]?.toUpperCase() || 'U'}
              </span>
            </div>
            {!isCollapsed && (
              <div className="text-sidebar-foreground overflow-hidden">
                <p className="font-medium text-sm truncate">{user?.username || 'User'}</p>
                <p className="text-xs text-sidebar-foreground/70">{user?.role || 'Role'}</p>
              </div>
            )}
          </div>

          {/* Navigation Menu */}
          <nav className="space-y-1 flex-1">
            {menuItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;

              const linkContent = (
                <Link
                  to={item.path}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
                    isActive
                      ? "bg-sidebar-primary text-sidebar-primary-foreground shadow-lg"
                      : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                    isCollapsed && "justify-center px-2"
                  )}
                >
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  {!isCollapsed && <span className="truncate">{item.label}</span>}
                </Link>
              );

              if (isCollapsed) {
                return (
                  <Tooltip key={item.path} delayDuration={0}>
                    <TooltipTrigger asChild>
                      {linkContent}
                    </TooltipTrigger>
                    <TooltipContent side="right" className="bg-sidebar text-sidebar-foreground border-sidebar-border">
                      {item.label}
                    </TooltipContent>
                  </Tooltip>
                );
              }

              return <div key={item.path}>{linkContent}</div>;
            })}
          </nav>

          {/* Logout Button */}
          <div className="pt-4 border-t border-sidebar-border">
            <Button
              onClick={handleLogout}
              variant="ghost"
              size={isCollapsed ? "icon" : "default"}
              className="w-full text-sidebar-foreground/70 hover:bg-destructive/20 hover:text-destructive justify-start"
            >
              <LogOut className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && <span className="ml-3">Logout</span>}
            </Button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto flex flex-col">
        {/* Top Bar with Date Filter and verif.ai Logo */}
        <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <div className="flex-1 max-w-md">
            <DateFilter
              onDateChange={setDateRange}
              showRefresh={false}
              className="shadow-none border-none bg-transparent"
            />
          </div>
          <img
            src={verifAiLogo}
            alt="verif.ai"
            className="h-16 object-contain"
          />
        </div>
        <div className="flex-1 overflow-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
