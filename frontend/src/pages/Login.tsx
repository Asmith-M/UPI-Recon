import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";

const Login = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const { login, isAuthenticated } = useAuth();

  // Redirect to dashboard when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate("/");
    }
  }, [isAuthenticated, navigate]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    const success = await login(username, password);
    if (!success) {
      setError("Invalid username or password");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-light to-brand-sky p-4">
      <Card className="w-full max-w-md shadow-2xl border-brand-blue/20">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold text-brand-dark">Login to UPI Recon</CardTitle>
          <CardDescription className="text-brand-mid">
            Enter your credentials to access the system
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username" className="text-brand-dark font-medium">
                Username
              </Label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="border-brand-blue/30 focus:border-brand-blue focus:ring-brand-blue/20"
                placeholder="Enter your username"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password" className="text-brand-dark font-medium">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="border-brand-blue/30 focus:border-brand-blue focus:ring-brand-blue/20"
                placeholder="Enter your password"
                required
              />
            </div>
            {error && (
              <p className="text-destructive text-sm text-center">{error}</p>
            )}
            <Button
              type="submit"
              className="w-full bg-brand-blue hover:bg-brand-mid text-white font-medium py-2 px-4 rounded-lg transition-colors"
            >
              Login
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default Login;
