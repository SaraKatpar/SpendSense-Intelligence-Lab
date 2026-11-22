import pk.spendsense.student.ServerAddress;
public class ServerAddressTest {
    private static void valid(String value){if(!ServerAddress.normalize(value).endsWith("/"))throw new AssertionError(value);}
    private static void invalid(String value){try{ServerAddress.normalize(value);}catch(IllegalArgumentException good){return;}throw new AssertionError("Accepted unsafe address: "+value);}
    public static void main(String[] args){
        valid("https://example.com");valid("https://example.com:8765/");valid("http://192.168.1.20:8765");valid("http://10.0.2.2:8765");valid("http://172.16.5.2:8765");
        for(String value:new String[]{"http://example.com","http://8.8.8.8","http://172.32.1.1","file:///etc/passwd","javascript:alert(1)","https://user:password@example.com","https://example.com/a","https://example.com?secret=x","http://192.168.999.2:8765","http://192.168.1.1:0","http://192.168.1.1:99999"})invalid(value);
        if(!ServerAddress.sameOrigin("https://example.com/","https://example.com:443/api/me"))throw new AssertionError("Default port mismatch");
        if(ServerAddress.sameOrigin("http://192.168.1.2:8765/","http://192.168.1.2:8766/"))throw new AssertionError("Different port accepted");
        if(ServerAddress.sameOrigin("https://example.com/","https://example.com.attacker.test/"))throw new AssertionError("Host suffix accepted");
        System.out.println("Server address and origin checks passed (19 cases).");
    }
}
