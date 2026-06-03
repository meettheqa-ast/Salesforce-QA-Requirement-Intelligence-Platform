"use client";

/**
 * Local wrapper around `react-zero-skeleton` (skelter).
 *
 * Why a wrapper: skelter is the chosen runtime skeleton library, but it is a
 * very new, single-maintainer package on the loading-state critical path. By
 * confining every import to this file, swapping it out later (or pinning a fork)
 * is a one-file change instead of a codebase-wide refactor. See DECISIONS.md D-0008.
 *
 * Usage:
 *   const SkeletonAware = withLoadingSkeleton(MyComponent);
 *   <SkeletonTheme animation="wave"><SkeletonAware isLoading={...} /></SkeletonTheme>
 *
 * skelter measures the real component's layout at runtime, so the skeleton stays
 * in sync with the component automatically -- there is no separate shape to keep
 * up to date. Animation/theme is controlled by the surrounding <SkeletonTheme>.
 */

import type { ComponentType } from "react";
import { SkeletonTheme, withSkeleton } from "react-zero-skeleton";

export function withLoadingSkeleton<P extends object>(
  Component: ComponentType<P>,
) {
  return withSkeleton(Component);
}

export { SkeletonTheme };
