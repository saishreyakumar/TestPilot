/**
 * AppWright Test: User Onboarding Flow
 * 
 * This test verifies the complete user onboarding experience
 * including account creation, profile setup, and first-time tutorial.
 */

const { test, expect } = require('@appwright/test');

test.describe('User Onboarding', () => {
    test.beforeEach(async ({ page }) => {
        // Reset app to initial state
        await page.reset();
    });

    test('should complete full onboarding flow', async ({ page }) => {
        // Test data
        const userData = {
            email: 'test@example.com',
            password: 'SecurePass123!',
            firstName: 'John',
            lastName: 'Doe',
            phoneNumber: '+1234567890'
        };

        // Step 1: Welcome screen
        await test.step('Navigate welcome screen', async () => {
            await expect(page.locator('[data-testid="welcome-title"]')).toBeVisible();
            await expect(page.locator('[data-testid="welcome-subtitle"]')).toContainText('Welcome to QualGent');
            
            await page.locator('[data-testid="get-started-button"]').click();
        });

        // Step 2: Account creation
        await test.step('Create new account', async () => {
            await expect(page.locator('[data-testid="signup-form"]')).toBeVisible();
            
            // Fill signup form
            await page.locator('[data-testid="email-input"]').fill(userData.email);
            await page.locator('[data-testid="password-input"]').fill(userData.password);
            await page.locator('[data-testid="confirm-password-input"]').fill(userData.password);
            
            // Accept terms
            await page.locator('[data-testid="terms-checkbox"]').check();
            
            // Submit form
            await page.locator('[data-testid="signup-button"]').click();
            
            // Wait for verification screen
            await expect(page.locator('[data-testid="verification-screen"]')).toBeVisible();
        });

        // Step 3: Email verification (simulate)
        await test.step('Verify email', async () => {
            // In a real test, this might involve checking email or using a mock
            await page.locator('[data-testid="skip-verification"]').click();
            
            await expect(page.locator('[data-testid="profile-setup"]')).toBeVisible();
        });

        // Step 4: Profile setup
        await test.step('Setup user profile', async () => {
            await page.locator('[data-testid="first-name-input"]').fill(userData.firstName);
            await page.locator('[data-testid="last-name-input"]').fill(userData.lastName);
            await page.locator('[data-testid="phone-input"]').fill(userData.phoneNumber);
            
            // Select profile picture (optional)
            await page.locator('[data-testid="profile-picture-option-1"]').click();
            
            await page.locator('[data-testid="save-profile-button"]').click();
            
            await expect(page.locator('[data-testid="tutorial-screen"]')).toBeVisible();
        });

        // Step 5: Tutorial walkthrough
        await test.step('Complete tutorial', async () => {
            // Tutorial step 1
            await expect(page.locator('[data-testid="tutorial-title"]')).toContainText('Getting Started');
            await page.locator('[data-testid="tutorial-next"]').click();
            
            // Tutorial step 2
            await expect(page.locator('[data-testid="tutorial-feature-highlight"]')).toBeVisible();
            await page.locator('[data-testid="tutorial-next"]').click();
            
            // Tutorial step 3
            await expect(page.locator('[data-testid="tutorial-tips"]')).toBeVisible();
            await page.locator('[data-testid="tutorial-finish"]').click();
            
            // Should reach main dashboard
            await expect(page.locator('[data-testid="main-dashboard"]')).toBeVisible();
            await expect(page.locator('[data-testid="welcome-message"]')).toContainText(`Welcome, ${userData.firstName}!`);
        });

        // Step 6: Verify onboarding completion
        await test.step('Verify onboarding state', async () => {
            // Check that user preferences are set
            await page.locator('[data-testid="user-menu"]').click();
            await expect(page.locator('[data-testid="user-name"]')).toContainText(`${userData.firstName} ${userData.lastName}`);
            
            // Verify tutorial badge or completion indicator
            await expect(page.locator('[data-testid="onboarding-complete-badge"]')).toBeVisible();
            
            // Check that onboarding flow doesn't appear on next app launch
            await page.reload();
            await expect(page.locator('[data-testid="main-dashboard"]')).toBeVisible();
            await expect(page.locator('[data-testid="welcome-screen"]')).not.toBeVisible();
        });
    });

    test('should handle email already exists error', async ({ page }) => {
        const existingEmail = 'existing@example.com';
        
        await page.locator('[data-testid="get-started-button"]').click();
        
        await page.locator('[data-testid="email-input"]').fill(existingEmail);
        await page.locator('[data-testid="password-input"]').fill('password123');
        await page.locator('[data-testid="confirm-password-input"]').fill('password123');
        await page.locator('[data-testid="terms-checkbox"]').check();
        
        await page.locator('[data-testid="signup-button"]').click();
        
        // Should show error message
        await expect(page.locator('[data-testid="error-message"]')).toContainText('Email already exists');
        await expect(page.locator('[data-testid="login-link"]')).toBeVisible();
    });

    test('should validate password requirements', async ({ page }) => {
        await page.locator('[data-testid="get-started-button"]').click();
        
        await page.locator('[data-testid="email-input"]').fill('test@example.com');
        
        // Test weak password
        await page.locator('[data-testid="password-input"]').fill('123');
        await expect(page.locator('[data-testid="password-strength"]')).toContainText('Weak');
        
        // Test medium password
        await page.locator('[data-testid="password-input"]').fill('password123');
        await expect(page.locator('[data-testid="password-strength"]')).toContainText('Medium');
        
        // Test strong password
        await page.locator('[data-testid="password-input"]').fill('SecurePass123!');
        await expect(page.locator('[data-testid="password-strength"]')).toContainText('Strong');
    });

    test('should allow skipping optional profile fields', async ({ page }) => {
        await page.locator('[data-testid="get-started-button"]').click();
        
        // Complete required signup
        await page.locator('[data-testid="email-input"]').fill('minimal@example.com');
        await page.locator('[data-testid="password-input"]').fill('SecurePass123!');
        await page.locator('[data-testid="confirm-password-input"]').fill('SecurePass123!');
        await page.locator('[data-testid="terms-checkbox"]').check();
        await page.locator('[data-testid="signup-button"]').click();
        
        // Skip verification
        await page.locator('[data-testid="skip-verification"]').click();
        
        // Skip profile setup
        await page.locator('[data-testid="skip-profile-button"]').click();
        
        // Should still reach dashboard
        await expect(page.locator('[data-testid="main-dashboard"]')).toBeVisible();
    });
}); 