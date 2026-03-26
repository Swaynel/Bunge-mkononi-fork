export function extractDigits(value: string) {
  return value.replace(/\D/g, '');
}

export function formatKenyanPhoneNumber(value: string) {
  const trimmed = value.trim();
  const digits = extractDigits(trimmed);

  if (!digits && !trimmed.includes('+')) {
    return '';
  }

  const internationalMode = trimmed.startsWith('+') || digits.startsWith('254');
  const nationalDigits = internationalMode
    ? (digits.startsWith('254') ? digits.slice(3) : digits).slice(0, 9)
    : (digits.startsWith('0') ? digits.slice(1) : digits).slice(0, 9);

  if (internationalMode) {
    if (!nationalDigits) {
      return '+254';
    }

    const parts = [nationalDigits.slice(0, 3), nationalDigits.slice(3, 6), nationalDigits.slice(6, 9)].filter(Boolean);
    return `+254 ${parts.join(' ')}`;
  }

  const localDigits = (digits.startsWith('0') ? digits.slice(0, 10) : `0${digits}`).slice(0, 10);
  const localParts = [localDigits.slice(0, 4), localDigits.slice(4, 7), localDigits.slice(7, 10)].filter(Boolean);
  return localParts.join(' ');
}

export function normalizeKenyanPhoneNumber(value: string) {
  const digits = extractDigits(value);
  if (!digits) {
    return '';
  }

  const nationalDigits = digits.startsWith('254')
    ? digits.slice(3, 12)
    : digits.startsWith('0')
      ? digits.slice(1, 10)
      : digits.slice(0, 9);

  if (nationalDigits.length !== 9) {
    return '';
  }

  return `+254${nationalDigits}`;
}
