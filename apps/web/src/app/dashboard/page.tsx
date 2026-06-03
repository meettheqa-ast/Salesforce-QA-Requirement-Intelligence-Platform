"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { SkeletonTheme, withLoadingSkeleton } from "@/components/skeleton";
import { api, type WhoAmI } from "@/lib/api";
import { useAuth } from "@/lib/auth";

function PrincipalCard({ data }: { data?: WhoAmI }) {
  const rows: Array<[string, string]> = [
    ["User", data?.user_id ?? "user-dev-1"],
    ["Tenant", data?.tenant_id ?? "tenant-dev-1"],
    ["Email", data?.email ?? "dev@example.com"],
    ["Role", data?.role ?? "tenant_admin"],
  ];
  return (
    <Card>
      <CardHeader>
        <CardTitle>Session</CardTitle>
        <CardDescription>Verified against the API /auth/me endpoint.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {rows.map(([label, value]) => (
          <div key={label} className="flex justify-between text-sm">
            <span className="text-muted-foreground">{label}</span>
            <span className="font-medium">{value}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// skelter auto-measures PrincipalCard's real layout to render its skeleton.
const PrincipalCardWithSkeleton = withLoadingSkeleton(PrincipalCard);

export default function DashboardPage() {
  const router = useRouter();
  const { token, setToken, isReady } = useAuth();

  React.useEffect(() => {
    if (isReady && !token) router.replace("/");
  }, [isReady, token, router]);

  const me = useQuery({
    queryKey: ["me", token],
    queryFn: () => api.whoami(token as string),
    enabled: Boolean(token),
  });

  return (
    <main className="container py-10">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Sprint 0 shell. Modules light up in later sprints.
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => {
            setToken(null);
            router.replace("/");
          }}
        >
          Sign out
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <SkeletonTheme animation="wave">
          <PrincipalCardWithSkeleton
            isLoading={me.isLoading}
            data={me.data}
          />
        </SkeletonTheme>
        <Card>
          <CardHeader>
            <CardTitle>Modules</CardTitle>
            <CardDescription>
              Connections, repositories, analysis, QA, and more arrive in Sprint 1+.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              The backend is a modular monolith with enforced boundaries; each
              module exposes its UI here as it ships.
            </p>
          </CardContent>
        </Card>
      </div>

      {me.isError ? (
        <p className="mt-4 text-sm text-destructive">
          Could not load session. Your token may have expired — sign out and back in.
        </p>
      ) : null}
    </main>
  );
}
