# Release checklist

## Public beta

1. Confirm `addon/manifest.ini` contains the intended semantic version and current NVDA API versions.
2. Push the source to `dgl1984/dictation-bridge-lite` with `main` as the default branch.
3. Let the **Build add-on** workflow complete successfully.
4. Download that workflow's add-on artifact and repeat the Notepad installation, partial-phrase, selection-replacement, and NVDA-restart tests.
5. Create and push a tag such as `v0.2.1-beta.1`. The release workflow verifies that the tag begins with the manifest version, rebuilds both architectures, and attaches only the versioned `.nvda-addon` to the release.
6. Confirm the release has exactly one uploaded asset: the `.nvda-addon`. GitHub's automatic source archives are expected and do not need to be uploaded separately.
7. Compare the add-on's SHA-256 digest with the value recorded in the release workflow summary, then verify installation once more.
8. Submit the release asset to VirusTotal. Native observation hooks may require false-positive review.
9. Recruit Windows 10 and Windows 11 beta testers using the issue template.

## NVDA Add-on Store

1. Use the direct GitHub release asset URL ending in `.nvda-addon`.
2. Open the NV Access Add-on Store registration issue form.
3. Select the beta channel until the remaining compatibility matrix is covered.
4. Use the repository, license, support, and download HTTPS URLs from this project.
5. Respond to automated validation or VirusTotal results on the generated submission issue.
6. After acceptance, announce the Add-on Store listing rather than circulating an unversioned attachment.

Official submission guide: <https://github.com/nvaccess/addon-datastore/blob/master/docs/submitters/submissionGuide.md>
