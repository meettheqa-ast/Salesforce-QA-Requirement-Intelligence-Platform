"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/**
 * Dev login page.
 *
 * In Sprint 0 there is no real IdP. This form calls the API's /auth/dev-token
 * endpoint (only enabled when AUTH_PROVIDER=dev) to mint a local bearer token,
 * then redirects to the dashboard. Sprint 1 replaces this with a real OIDC flow.
 */
export default function DevLoginPage() {
  const router = useRouter();
  const { token, setToken, isReady } = useAuth();
  const [tenantId, setTenantId] = React.useState("tenant-dev-1");
  const [userId, setUserId] = React.useState("user-dev-1");
  const [email, setEmail] = React.useState("dev@example.com");

  React.useEffect(() => {
    if (isReady && token) router.replace("/dashboard");
  }, [isReady, token, router]);

  const login = useMutation({
    mutationFn: () =>
      api.mintDevToken({
        user_id: userId,
        tenant_id: tenantId,
        email,
        role: "tenant_admin",
      }),
    onSuccess: (res) => {
      setToken(res.access_token);
      router.replace("/dashboard");
    },
  });

  return (
    <main className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>SFQA Intelligence</CardTitle>
          <CardDescription>
            Developer sign-in. Mints a local token via the API dev provider.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-sm font-medium" htmlFor="tenantId">
              Tenant ID
            </label>
            <Input
              id="tenantId"
              value={tenantId}
              onChange={(e) => setTenantId(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium" htmlFor="userId">
              User ID
            </label>
            <Input
              id="userId"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium" htmlFor="email">
              Email
            </label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          {login.isError ? (
            <p className="text-sm text-destructive">
              {login.error instanceof ApiError
                ? `${login.error.status}: ${login.error.message}`
                : "Sign-in failed. Is the API running on " +
                  "http://localhost:8000?"}
            </p>
          ) : null}
        </CardContent>
        <CardFooter>
          <Button
            className="w-full"
            onClick={() => login.mutate()}
            disabled={login.isPending}
          >
            {login.isPending ? "Signing in..." : "Sign in (dev)"}
          </Button>
        </CardFooter>
      </Card>
    </main>
  );
}
