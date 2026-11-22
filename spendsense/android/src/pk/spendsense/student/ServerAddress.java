package pk.spendsense.student;

import java.net.URI;
import java.util.Locale;

/** Pure Java validation, shared by the native connection screen and JVM checks. */
public final class ServerAddress {
    private ServerAddress() {}
    public static String normalize(String input) {
        try {
            URI uri = new URI(input.trim());
            String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase(Locale.ROOT);
            String host = uri.getHost();
            if (host == null || uri.getRawUserInfo() != null || uri.getRawQuery() != null || uri.getRawFragment() != null
                || !(uri.getRawPath() == null || uri.getRawPath().isEmpty() || uri.getRawPath().equals("/"))
                || uri.getPort() > 65535 || uri.getPort() == 0 || !(scheme.equals("https") || scheme.equals("http"))) {
                throw new IllegalArgumentException();
            }
            if (scheme.equals("http") && !privateIPv4(host)) {
                throw new IllegalArgumentException("HTTP is only supported for a private Wi-Fi IPv4 address. Use HTTPS for a public server.");
            }
            return new URI(scheme, null, host.toLowerCase(Locale.ROOT), uri.getPort(), "/", null, null).toString();
        } catch (Exception error) {
            if (error instanceof IllegalArgumentException && error.getMessage() != null) throw (IllegalArgumentException)error;
            throw new IllegalArgumentException("Enter your server origin, for example https://spendsense.example.com or http://192.168.1.20:8765");
        }
    }
    public static boolean privateIPv4(String host) {
        String[] parts = host.split("\\.");
        if (parts.length != 4) return false;
        int[] p = new int[4];
        try {
            for (int i=0;i<4;i++) {
                if (!parts[i].matches("0|[1-9][0-9]{0,2}")) return false;
                p[i]=Integer.parseInt(parts[i]);if(p[i]>255) return false;
            }
        } catch(NumberFormatException error) {return false;}
        return p[0]==10 || (p[0]==192 && p[1]==168) || (p[0]==172 && p[1]>=16 && p[1]<=31);
    }
    public static boolean sameOrigin(String first,String second) {
        try {
            URI a=new URI(first),b=new URI(second);
            return a.getScheme()!=null && a.getScheme().equalsIgnoreCase(b.getScheme()) && a.getHost()!=null && a.getHost().equalsIgnoreCase(b.getHost()) && port(a)==port(b);
        } catch(Exception error) {return false;}
    }
    private static int port(URI uri) {return uri.getPort()==-1?("https".equalsIgnoreCase(uri.getScheme())?443:80):uri.getPort();}
}
