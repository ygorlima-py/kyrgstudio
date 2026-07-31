export type AccessTokenRefresh = () => Promise<string>

/**
 * Ensures concurrent authentication failures share one refresh operation.
 */
export class RefreshCoordinator {
  private activeRefresh: Promise<string> | null = null

  refresh(refreshAccessToken: AccessTokenRefresh): Promise<string> {
    if (this.activeRefresh !== null) {
      return this.activeRefresh
    }

    this.activeRefresh = this.executeRefresh(refreshAccessToken)
    return this.activeRefresh
  }

  private async executeRefresh(refreshAccessToken: AccessTokenRefresh): Promise<string> {
    try {
      const refreshedToken = (await refreshAccessToken()).trim()

      if (refreshedToken.length === 0) {
        throw new Error('Access token refresh returned an empty token.')
      }

      return refreshedToken
    } finally {
      this.activeRefresh = null
    }
  }
}

export const accessTokenRefreshCoordinator = new RefreshCoordinator()
