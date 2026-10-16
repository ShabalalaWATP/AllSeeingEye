package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func expiryTime(t *testing.T) time.Time {
	t.Helper()
	end, err := time.Parse(time.RFC3339, strings.TrimSpace(expiry))
	if err != nil {
		t.Fatal(err)
	}
	return end
}

func TestRequiredFields(t *testing.T) {
	for _, contact := range []string{"mailto:security@example.test", "https://example.test/private-report"} {
		body, warning, err := renderDefault("https://example.test:8443/", contact, expiryTime(t).AddDate(0, -6, 0))
		if err != nil || warning != "" {
			t.Fatalf("render failed: %v, %s", err, warning)
		}
		for _, field := range []string{"Contact: " + contact, "Expires: " + strings.TrimSpace(expiry), "Preferred-Languages: en", "Policy: " + policy, "Canonical: https://example.test:8443/.well-known/security.txt"} {
			if !strings.Contains(body, field+"\n") {
				t.Errorf("missing %s", field)
			}
		}
		if strings.Contains(body, "allseeingeyeosint.com") || len(strings.Split(strings.TrimSpace(body), "\n")) != 5 {
			t.Fatal("unexpected deployment or additional fields")
		}
	}
}

func TestInvalidConfiguration(t *testing.T) {
	for _, contact := range []string{" ", "http://example.test", "javascript:alert(1)", "mailto:a@example.test\nExpires: forged", "mailto:a@example.test?subject=public", "mailto:a@example.test,b@example.test", "https://example.test/%0aContact:injected", "https://user:password@example.test/report", "https://example.test/report?token=private", "https://example.test/#fragment", "https://example.test/é", strings.Repeat("x", 2049), "https://example.test/%xx", "https://-bad.test/report", "https://example.test:99999/report"} {
		t.Run(contact, func(t *testing.T) {
			if _, _, err := renderDefault("https://example.test", contact, expiryTime(t).AddDate(0, -6, 0)); err == nil {
				t.Fatal("invalid contact accepted")
			}
		})
	}
	for _, base := range []string{"", "http://localhost:5173", "https://example.test/app", "https://example.test/?", "https://example.test/?secret=x", "https://example.test/#fragment", "https://user@example.test", "https://example.test:\\x", "https://bad..test", "https://example.test:0", "https://example.test:", "https://[invalid]"} {
		t.Run(base, func(t *testing.T) {
			if _, _, err := renderDefault(base, "mailto:a@example.test", expiryTime(t).AddDate(0, -6, 0)); err == nil {
				t.Fatal("invalid public origin accepted")
			}
		})
	}
}

func TestDisabledAndExpiry(t *testing.T) {
	end := expiryTime(t)
	if body, warning, err := renderDefault("http://localhost", "", end); body != "" || warning != "" || err != nil {
		t.Fatal("blank contact must disable publication even without HTTPS configuration")
	}
	for _, remaining := range []time.Duration{30 * 24 * time.Hour, time.Hour, 0, -time.Hour} {
		body, warning, err := renderDefault("https://example.test", "mailto:a@example.test", end.Add(-remaining))
		if err != nil || warning == "" || (body == "") != (remaining <= 0) {
			t.Fatalf("incorrect expiry behaviour at %s", remaining)
		}
	}
	if _, _, err := renderDefault("https://example.test", "mailto:a@example.test", end.AddDate(-1, 0, -1)); err == nil {
		t.Fatal("expiry beyond a year accepted")
	}
	if _, _, err := renderDefault("https://[::1]:8443", "mailto:a@example.test", end.AddDate(0, -6, 0)); err != nil {
		t.Fatal("valid IPv6 origin rejected")
	}
}

func TestPublishAndDisable(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "private")
	if err := publish(dir, "first\n"); err != nil {
		t.Fatal(err)
	}
	if err := publish(dir, "second\n"); err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(filepath.Join(dir, "security.txt"))
	if err != nil || string(data) != "second\n" {
		t.Fatal("contact was not replaced")
	}
	for range 2 {
		if err := publish(dir, ""); err != nil {
			t.Fatal(err)
		}
	}
	if _, err := os.Stat(filepath.Join(dir, "security.txt")); !os.IsNotExist(err) {
		t.Fatal("disabled contact remains published")
	}
}

func TestFilesystemBoundaries(t *testing.T) {
	root := t.TempDir()
	outside := filepath.Join(root, "unrelated.txt")
	if err := os.WriteFile(outside, []byte("preserve"), 0600); err != nil {
		t.Fatal(err)
	}
	linked := filepath.Join(root, "linked")
	if err := os.Symlink(root, linked); err != nil {
		t.Fatal(err)
	}
	if err := publish(linked, "bad"); err == nil {
		t.Fatal("linked directory accepted")
	}
	dir := filepath.Join(root, "private")
	if err := publish(dir, ""); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, filepath.Join(dir, "security.txt")); err != nil {
		t.Fatal(err)
	}
	if err := publish(dir, "safe"); err != nil {
		t.Fatal(err)
	}
	data, _ := os.ReadFile(outside)
	if string(data) != "preserve" {
		t.Fatal("followed a target link")
	}
	if err := os.Chmod(dir, 0755); err != nil {
		t.Fatal(err)
	}
	if err := publish(dir, "bad"); err == nil {
		t.Fatal("public directory accepted")
	}
}

func TestCanonicalRejectsEncodedPathAndEmptyFragment(t *testing.T) {
	for _, base := range []string{"https://example.test/%2f", "https://example.test/#"} {
		if _, _, err := renderDefault(base, "mailto:a@example.test", expiryTime(t).AddDate(0, -6, 0)); err == nil {
			t.Fatal("ambiguous canonical accepted")
		}
	}
}

func TestMainPublishesConfiguredContact(t *testing.T) {
	saved := expiry
	t.Cleanup(func() { expiry = saved })
	expiry = time.Now().UTC().Add(24 * time.Hour).Format(time.RFC3339)
	t.Setenv("ASE_SECURITY_POLICY", "")
	t.Setenv("ASE_PUBLIC_BASE_URL", "https://operator.example.test")
	t.Setenv("ASE_SECURITY_CONTACT", "mailto:operator@example.test")
	main()
	data, err := os.ReadFile(filepath.Join(outputDir, "security.txt"))
	if err != nil || !strings.Contains(string(data), "Contact: mailto:operator@example.test\n") {
		t.Fatal("entrypoint did not publish configured contact")
	}
	t.Setenv("ASE_SECURITY_CONTACT", "")
	main()
	if _, err := os.Stat(filepath.Join(outputDir, "security.txt")); !os.IsNotExist(err) {
		t.Fatal("entrypoint did not disable publication")
	}
}

func renderDefault(base, contact string, now time.Time) (string, string, error) {
	return render(base, contact, policy, now)
}

func TestOperatorPolicy(t *testing.T) {
	body, _, err := render("https://example.test", "mailto:a@example.test", "https://example.test/disclosure", expiryTime(t).AddDate(0, -6, 0))
	if err != nil || !strings.Contains(body, "Policy: https://example.test/disclosure\n") {
		t.Fatal("operator policy missing")
	}
	if _, _, err := render("https://example.test", "mailto:a@example.test", "http://example.test/policy", expiryTime(t).AddDate(0, -6, 0)); err == nil {
		t.Fatal("unsafe policy accepted")
	}
}
