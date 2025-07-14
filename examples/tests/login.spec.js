/**
 * AppWright Test: User Login Functionality
 * 
 * This test suite covers various login scenarios including
 * successful login, error handling, and authentication flows.
 */

const { test, expect } = require('@appwright/test');

test.describe('User Login', () => {
    const validCredentials = {
        email: 'user@qualgent.com',
        password: 'ValidPass123!'
    };

    test.beforeEach(async ({ page }) => {
        // Ensure we're logged out and on login screen
        await page.reset();
        await page.goto('/login');
    });

    test('should login successfully with valid credentials', async ({ page }) => {
        await test.step('Enter valid credentials', async () => {
            await page.locator('[data-testid="email-input"]').fill(validCredentials.email);
            await page.locator('[data-testid="password-input"]').fill(validCredentials.password);
        });

        await test.step('Submit login form', async () => {
            await page.locator('[data-testid="login-button"]').click();
        });

        await test.step('Verify successful login', async () => {
            // Should redirect to dashboard
            await expect(page.locator('[data-testid="main-dashboard"]')).toBeVisible();
            
            // Should show user profile
            await expect(page.locator('[data-testid="user-avatar"]')).toBeVisible();
            
            // Should show logout option
            await page.locator('[data-testid="user-menu"]').click();
            await expect(page.locator('[data-testid="logout-button"]')).toBeVisible();
        });
    });

    test('should show error for invalid email', async ({ page }) => {
        await page.locator('[data-testid="email-input"]').fill('invalid-email');
        await page.locator('[data-testid="password-input"]').fill(validCredentials.password);
        await page.locator('[data-testid="login-button"]').click();

        await expect(page.locator('[data-testid="email-error"]')).toContainText('Please enter a valid email address');
        await expect(page.locator('[data-testid="main-dashboard"]')).not.toBeVisible();
    });

    test('should show error for incorrect password', async ({ page }) => {
        await page.locator('[data-testid="email-input"]').fill(validCredentials.email);
        await page.locator('[data-testid="password-input"]').fill('wrongpassword');
        await page.locator('[data-testid="login-button"]').click();

        await expect(page.locator('[data-testid="login-error"]')).toContainText('Invalid email or password');
        await expect(page.locator('[data-testid="main-dashboard"]')).not.toBeVisible();
    });

    test('should show error for non-existent user', async ({ page }) => {
        await page.locator('[data-testid="email-input"]').fill('nonexistent@example.com');
        await page.locator('[data-testid="password-input"]').fill('anypassword');
        await page.locator('[data-testid="login-button"]').click();

        await expect(page.locator('[data-testid="login-error"]')).toContainText('Invalid email or password');
    });

    test('should validate required fields', async ({ page }) => {
        await test.step('Try login without email', async () => {
            await page.locator('[data-testid="password-input"]').fill(validCredentials.password);
            await page.locator('[data-testid="login-button"]').click();
            
            await expect(page.locator('[data-testid="email-error"]')).toContainText('Email is required');
        });

        await test.step('Try login without password', async () => {
            await page.locator('[data-testid="email-input"]').fill(validCredentials.email);
            await page.locator('[data-testid="password-input"]').clear();
            await page.locator('[data-testid="login-button"]').click();
            
            await expect(page.locator('[data-testid="password-error"]')).toContainText('Password is required');
        });
    });

    test('should handle remember me functionality', async ({ page }) => {
        await page.locator('[data-testid="email-input"]').fill(validCredentials.email);
        await page.locator('[data-testid="password-input"]').fill(validCredentials.password);
        
        // Check remember me
        await page.locator('[data-testid="remember-me-checkbox"]').check();
        await page.locator('[data-testid="login-button"]').click();

        await expect(page.locator('[data-testid="main-dashboard"]')).toBeVisible();

        // Simulate app restart (reload page)
        await page.reload();

        // Should remain logged in
        await expect(page.locator('[data-testid="main-dashboard"]')).toBeVisible();
        await expect(page.locator('[data-testid="login-screen"]')).not.toBeVisible();
    });

    test('should navigate to forgot password', async ({ page }) => {
        await page.locator('[data-testid="forgot-password-link"]').click();
        
        await expect(page.locator('[data-testid="forgot-password-screen"]')).toBeVisible();
        await expect(page.locator('[data-testid="reset-email-input"]')).toBeVisible();
    });

    test('should navigate to signup screen', async ({ page }) => {
        await page.locator('[data-testid="signup-link"]').click();
        
        await expect(page.locator('[data-testid="signup-screen"]')).toBeVisible();
        await expect(page.locator('[data-testid="signup-form"]')).toBeVisible();
    });

    test('should handle social login options', async ({ page }) => {
        await test.step('Verify social login buttons', async () => {
            await expect(page.locator('[data-testid="google-login-button"]')).toBeVisible();
            await expect(page.locator('[data-testid="facebook-login-button"]')).toBeVisible();
            await expect(page.locator('[data-testid="apple-login-button"]')).toBeVisible();
        });

        // Note: Testing actual social login would require additional setup
        // In a real scenario, you might mock these interactions
    });

    test('should show loading state during login', async ({ page }) => {
        // Intercept login request to delay it
        await page.route('**/api/auth/login', async route => {
            await new Promise(resolve => setTimeout(resolve, 1000));
            await route.continue();
        });

        await page.locator('[data-testid="email-input"]').fill(validCredentials.email);
        await page.locator('[data-testid="password-input"]').fill(validCredentials.password);
        await page.locator('[data-testid="login-button"]').click();

        // Should show loading state
        await expect(page.locator('[data-testid="login-loading"]')).toBeVisible();
        await expect(page.locator('[data-testid="login-button"]')).toBeDisabled();

        // Eventually should complete
        await expect(page.locator('[data-testid="main-dashboard"]')).toBeVisible({ timeout: 5000 });
    });

    test('should handle session timeout', async ({ page }) => {
        // Login first
        await page.locator('[data-testid="email-input"]').fill(validCredentials.email);
        await page.locator('[data-testid="password-input"]').fill(validCredentials.password);
        await page.locator('[data-testid="login-button"]').click();
        
        await expect(page.locator('[data-testid="main-dashboard"]')).toBeVisible();

        // Simulate session timeout by clearing storage
        await page.evaluate(() => {
            localStorage.clear();
            sessionStorage.clear();
        });

        // Try to access protected resource
        await page.locator('[data-testid="user-menu"]').click();

        // Should redirect to login with session timeout message
        await expect(page.locator('[data-testid="login-screen"]')).toBeVisible();
        await expect(page.locator('[data-testid="session-timeout-message"]')).toContainText('Session expired. Please log in again.');
    });

    test('should maintain login state across tabs', async ({ context, page }) => {
        // Login in first tab
        await page.locator('[data-testid="email-input"]').fill(validCredentials.email);
        await page.locator('[data-testid="password-input"]').fill(validCredentials.password);
        await page.locator('[data-testid="login-button"]').click();
        
        await expect(page.locator('[data-testid="main-dashboard"]')).toBeVisible();

        // Open new tab
        const newPage = await context.newPage();
        await newPage.goto('/');

        // Should be logged in in new tab too
        await expect(newPage.locator('[data-testid="main-dashboard"]')).toBeVisible();
        await expect(newPage.locator('[data-testid="login-screen"]')).not.toBeVisible();
    });
}); 