import { getRequestConfig } from "next-intl/server";
import { loadLocaleMessages } from "@/lib/i18n";

export default getRequestConfig(async () => loadLocaleMessages());
