import { ReactNode, useState, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
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
  const { logout } = useAuth();
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

  // Handle logout
  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="flex min-h-screen w-full bg-background">
      {/* Sidebar */}
      <aside 
        className={cn(
          "bg-brand-dark border-r border-brand-blue shadow-xl transition-all duration-300 ease-in-out flex flex-col",
          isCollapsed ? "w-16" : "w-64"
        )}
      >
        <div className="p-3 flex-1 flex flex-col">
          {/* Toggle Button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className="mb-4 self-end text-primary-foreground hover:bg-brand-blue/50"
          >
            {isCollapsed ? (
              <PanelLeft className="w-5 h-5" />
            ) : (
              <PanelLeftClose className="w-5 h-5" />
            )}
          </Button>

          {/* User Info */}
          <div className={cn(
            "flex items-center gap-3 mb-6 pb-4 border-b border-brand-blue",
            isCollapsed && "justify-center"
          )}>
            <div className="w-10 h-10 rounded-full bg-brand-sky flex items-center justify-center flex-shrink-0">
              <span className="text-primary-foreground font-semibold">NS</span>
            </div>
            {!isCollapsed && (
              <div className="text-primary-foreground overflow-hidden">
                <p className="font-medium text-sm truncate">User: NSTX00001</p>
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
                      ? "bg-brand-blue text-primary-foreground shadow-lg"
                      : "text-primary-foreground/70 hover:bg-brand-blue/50 hover:text-primary-foreground",
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
                    <TooltipContent side="right" className="bg-brand-dark text-primary-foreground border-brand-blue">
                      {item.label}
                    </TooltipContent>
                  </Tooltip>
                );
              }

              return <div key={item.path}>{linkContent}</div>;
            })}
          </nav>

          {/* Logout Button */}
          <div className="mt-auto pt-4 border-t border-brand-blue">
            <Button
              onClick={handleLogout}
              variant="ghost"
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2.5 text-primary-foreground/70 hover:bg-red-600/50 hover:text-primary-foreground transition-all",
                isCollapsed && "justify-center px-2"
              )}
            >
              <LogOut className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && <span>Logout</span>}
            </Button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
