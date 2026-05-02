import { createClient, SupabaseClient } from "@supabase/supabase-js";

const url = process.env.SUPABASE_URL;
const serviceKey = process.env.SUPABASE_SERVICE_KEY;
const userId = process.env.ONTRACK_USER_ID;

if (!url) throw new Error("SUPABASE_URL is required");
if (!serviceKey) throw new Error("SUPABASE_SERVICE_KEY is required");
if (!userId) throw new Error("ONTRACK_USER_ID is required");

export const supabase: SupabaseClient = createClient(url, serviceKey, {
    auth: { persistSession: false, autoRefreshToken: false },
});

export const USER_ID: string = userId;
