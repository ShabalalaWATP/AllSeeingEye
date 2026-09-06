import { Alert } from '@/components/ui/Alert';
import { useLanguageCatalogue } from '@/lib/hooks/useLanguageCatalogue';

const fallbackLabels: Record<string, string> = {
  ar: 'Arabic',
  fa: 'Persian',
  'zh-CN': 'Chinese (China)',
  'zh-TW': 'Chinese (Taiwan)',
};
/** Keep the existing renderer warning visible while capability metadata is unavailable. */
export function PdfLanguageNotice({ language }: { language?: string | undefined }) {
  const catalogue = useLanguageCatalogue();
  const capability = catalogue.data?.languages.find((entry) => entry.code === language);
  const label = capability?.label ?? fallbackLabels[language ?? ''];
  const unsupported = capability ? !capability.pdf_supported : Boolean(label);
  if (!unsupported) return null;
  return (
    <Alert tone="warning">
      PDF downloads cannot currently display {label} text correctly and replace unsupported
      characters with code labels. Choose DOCX or Markdown to preserve the original text.
    </Alert>
  );
}
