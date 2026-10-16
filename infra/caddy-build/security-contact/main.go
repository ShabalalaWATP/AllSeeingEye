// Generate installation-specific public contact data, never Caddy configuration.
package main

import (
	_ "embed"
	"errors"
	"fmt"
	"net/mail"
	"net/netip"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"
)

//go:embed expiry.txt
var expiry string

const outputDir = "/tmp/ase-security-contact"
const policy = "https://github.com/ShabalalaWATP/AllSeeingEye/security/policy"

var hostLabel = regexp.MustCompile(`^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$`)

func validHost(parsed *url.URL) bool {
	host := parsed.Hostname()
	if _, err := netip.ParseAddr(host); err != nil {
		if len(host) > 253 {
			return false
		}
		for _, label := range strings.Split(host, ".") {
			if !hostLabel.MatchString(label) {
				return false
			}
		}
	}
	if strings.HasSuffix(parsed.Host, ":") {
		return false
	}
	if parsed.Port() != "" {
		port, err := strconv.Atoi(parsed.Port())
		if err != nil || port < 1 || port > 65535 {
			return false
		}
	}
	return true
}

func plainURI(value string) bool {
	if len(value) == 0 || len(value) > 2048 {
		return false
	}
	decoded, err := url.PathUnescape(value)
	if err != nil {
		return false
	}
	for _, char := range decoded {
		if char <= 32 || char >= 127 || char == '\\' {
			return false
		}
	}
	return true
}

func httpsURL(value string) (*url.URL, error) {
	parsed, err := url.Parse(value)
	if !plainURI(value) || err != nil || parsed.Scheme != "https" || parsed.Hostname() == "" ||
		parsed.User != nil || parsed.Opaque != "" || strings.Contains(value, "#") || parsed.RawQuery != "" || parsed.ForceQuery || !validHost(parsed) {
		return nil, errors.New("expected an HTTPS URL without credentials, query or fragment")
	}
	return parsed, nil
}

func render(base, contact, policyURL string, now time.Time) (string, string, error) {
	if contact == "" {
		return "", "", nil
	}
	if !plainURI(contact) {
		return "", "", errors.New("invalid security contact URI")
	}
	if strings.HasPrefix(contact, "mailto:") {
		address := strings.TrimPrefix(contact, "mailto:")
		parsed, err := mail.ParseAddress(address)
		if err != nil || parsed.Address != address || strings.ContainsAny(address, "?%#") {
			return "", "", errors.New("expected a single mailto address without parameters")
		}
	} else if _, err := httpsURL(contact); err != nil {
		return "", "", errors.New("expected an HTTPS or mailto security contact")
	}
	if _, err := httpsURL(policyURL); err != nil {
		return "", "", errors.New("invalid security policy URL")
	}
	origin, err := httpsURL(base)
	if err != nil || origin.RawPath != "" || (origin.Path != "" && origin.Path != "/") {
		return "", "", errors.New("ASE_PUBLIC_BASE_URL must be an HTTPS origin")
	}
	expires := strings.TrimSpace(expiry)
	end, err := time.Parse(time.RFC3339, expires)
	if err != nil || end.After(now.AddDate(1, 0, 0)) {
		return "", "", errors.New("invalid reviewed security contact expiry")
	}
	if !end.After(now) {
		return "", "security.txt has expired; publication disabled until the image expiry is reviewed", nil
	}
	warning := ""
	if end.Sub(now) <= 30*24*time.Hour {
		warning = "security.txt expires within 30 days; review the contact and image expiry"
	}
	body := fmt.Sprintf("Contact: %s\nExpires: %s\nPreferred-Languages: en\nPolicy: %s\nCanonical: %s/.well-known/security.txt\n",
		contact, expires, policyURL, "https://"+origin.Host)
	return body, warning, nil
}

func publish(directory, body string) error {
	if err := os.Mkdir(directory, 0700); err != nil && !os.IsExist(err) {
		return err
	}
	info, err := os.Lstat(directory)
	if err != nil || !info.IsDir() || info.Mode().Perm() != 0700 {
		return errors.New("security contact directory must be a private real directory")
	}
	target := filepath.Join(directory, "security.txt")
	if body == "" {
		if err := os.Remove(target); err != nil && !os.IsNotExist(err) {
			return err
		}
		return nil
	}
	file, err := os.CreateTemp(directory, ".security-*")
	if err != nil {
		return err
	}
	defer os.Remove(file.Name())
	_, writeErr := file.WriteString(body)
	closeErr := file.Close()
	if writeErr != nil {
		return writeErr
	}
	if closeErr != nil {
		return closeErr
	}
	return os.Rename(file.Name(), target)
}

func main() {
	policyURL := os.Getenv("ASE_SECURITY_POLICY")
	if policyURL == "" {
		policyURL = policy
	}
	body, warning, err := render(os.Getenv("ASE_PUBLIC_BASE_URL"), os.Getenv("ASE_SECURITY_CONTACT"), policyURL, time.Now().UTC())
	if err == nil {
		err = publish(outputDir, body)
	}
	if err != nil {
		// Configuration values and raw filesystem errors may contain private details.
		fmt.Fprintln(os.Stderr, "security.txt configuration failed; check the public origin, contact URI and writable private /tmp")
		os.Exit(1)
	}
	if warning != "" {
		fmt.Fprintln(os.Stderr, warning)
	}
}
