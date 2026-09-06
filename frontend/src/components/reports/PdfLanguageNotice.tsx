import { Alert } from '@/components/ui/Alert';

/** The current PDF font cannot preserve Arabic or Chinese narrative text. */
export function PdfLanguageNotice({ language }: { language?: string | undefined }) {
  if (language !== 'ar' && language !== 'zh') return null;
  return (
    <Alert tone="warning">
      PDF downloads cannot currently display {language === 'ar' ? 'Arabic' : 'Chinese'} text
      correctly and replace unsupported characters with code labels. Choose DOCX or Markdown to
      preserve the original text.
    </Alert>
  );
}
