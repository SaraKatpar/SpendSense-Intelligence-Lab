package pk.spendsense.student;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.net.http.SslError;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.WindowInsets;
import android.webkit.CookieManager;
import android.webkit.SslErrorHandler;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.PopupMenu;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class MainActivity extends Activity {
    private final int BACKGROUND=Color.rgb(14,21,24), MINT=Color.rgb(167,229,199), TEXT=Color.rgb(238,244,241), MUTED=Color.rgb(169,187,182);
    private LinearLayout root;
    private FrameLayout content;
    private WebView web;
    private ProgressBar progress;
    private String server;
    private ValueCallback<Uri[]> upload;
    private byte[] exportBytes;
    private boolean failed;

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        server=getPreferences(MODE_PRIVATE).getString("server","");
        if(server.isEmpty()) showSetup(); else openWallet();
    }
    private int dp(int value){return Math.round(value*getResources().getDisplayMetrics().density);}
    private GradientDrawable rounded(int color){GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(16));return d;}
    private TextView text(String label,int size,int color){TextView t=new TextView(this);t.setText(label);t.setTextSize(size);t.setTextColor(color);t.setPadding(0,dp(6),0,dp(6));return t;}
    private Button button(String label){Button b=new Button(this);b.setText(label);b.setAllCaps(false);b.setTextColor(BACKGROUND);b.setBackground(rounded(MINT));b.setPadding(dp(16),dp(12),dp(16),dp(12));b.setMinHeight(dp(52));return b;}
    private void base(){
        root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setBackgroundColor(BACKGROUND);
        root.setOnApplyWindowInsetsListener((v,insets)->{v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());return insets.consumeSystemWindowInsets();});
        setContentView(root);root.requestApplyInsets();
    }
    private void showSetup(){
        if(web!=null){web.stopLoading();web.destroy();web=null;}
        base();ScrollView scroll=new ScrollView(this);LinearLayout layout=new LinearLayout(this);layout.setOrientation(LinearLayout.VERTICAL);layout.setPadding(dp(26),dp(35),dp(26),dp(30));scroll.addView(layout);root.addView(scroll);
        TextView logo=text("s✳  spendsense",27,MINT);logo.setTypeface(null,Typeface.BOLD);layout.addView(logo);
        TextView title=text("More campus.\nLess cash chaos.",36,TEXT);title.setPadding(0,dp(30),0,dp(12));layout.addView(title);
        layout.addView(text("Connect your student wallet",22,TEXT));
        layout.addView(text("Your database and Llama AI run on your laptop/server. Enter its address once, then sign in to your own account.",16,MUTED));
        layout.addView(text("SpendSense server address",15,MINT));
        EditText input=new EditText(this);input.setSingleLine(true);input.setTextColor(TEXT);input.setHintTextColor(MUTED);input.setText(server);input.setHint("https://your-server.example");input.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_URI);input.setPadding(dp(14),dp(13),dp(14),dp(13));input.setBackground(rounded(Color.rgb(28,45,36)));layout.addView(input);
        TextView error=text("",14,Color.rgb(240,187,161));layout.addView(error);
        Button connect=button("Connect my wallet");layout.addView(connect);
        connect.setOnClickListener(v->{try{
            String value=ServerAddress.normalize(input.getText().toString());
            Runnable save=()->{String old=server;server=value;getPreferences(MODE_PRIVATE).edit().putString("server",server).apply();if(!old.equals(server))CookieManager.getInstance().removeAllCookies(done->openWallet());else openWallet();};
            if(value.startsWith("http:"))new AlertDialog.Builder(this).setTitle("Local Wi-Fi preview").setMessage("This local connection uses HTTP. Use fictional data for testing; choose a trusted HTTPS server before using real credentials over a network. Keep your laptop running on the same Wi-Fi.").setNegativeButton("Edit address",null).setPositiveButton("Use local preview",(d,w)->save.run()).show();else save.run();
        }catch(IllegalArgumentException e){error.setText(e.getMessage());}});
        TextView help=text("On your laptop, run run_mobile_lan.bat. Find its Wi-Fi IPv4 address with ipconfig. Open port 8765 on the same trusted Wi-Fi. A university network may isolate devices.\n\nThis APK is a connected app. It does not bundle your private database or run the Python models on your phone.",15,MUTED);help.setPadding(0,dp(24),0,0);layout.addView(help);
    }
    @SuppressWarnings("deprecation") private void openWallet(){
        base();failed=false;
        LinearLayout bar=new LinearLayout(this);bar.setGravity(Gravity.CENTER_VERTICAL);bar.setPadding(dp(16),dp(4),dp(10),dp(4));bar.setBackgroundColor(Color.rgb(16,26,28));
        TextView title=text("s✳  SpendSense",17,MINT);title.setTypeface(null,Typeface.BOLD);bar.addView(title,new LinearLayout.LayoutParams(0,dp(48),1));
        Button menu=new Button(this);menu.setText("•••");menu.setTextColor(MINT);menu.setBackgroundColor(Color.TRANSPARENT);menu.setContentDescription("Connection and export options");bar.addView(menu,new LinearLayout.LayoutParams(dp(55),dp(48)));
        menu.setOnClickListener(v->{PopupMenu popup=new PopupMenu(this,menu);popup.getMenu().add("Change server");popup.getMenu().add("Export finances");popup.getMenu().add("Open in browser");popup.setOnMenuItemClickListener(item->{String name=item.getTitle().toString();if(name.equals("Change server"))showSetup();else if(name.equals("Export finances"))exportFinance();else startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(server)));return true;});popup.show();});
        root.addView(bar);progress=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);progress.setMax(100);root.addView(progress,new LinearLayout.LayoutParams(-1,dp(3)));
        content=new FrameLayout(this);root.addView(content,new LinearLayout.LayoutParams(-1,0,1));
        web=new WebView(this);web.setBackgroundColor(BACKGROUND);content.addView(web,new FrameLayout.LayoutParams(-1,-1));
        WebSettings settings=web.getSettings();settings.setJavaScriptEnabled(true);settings.setDomStorageEnabled(true);settings.setAllowFileAccess(false);settings.setAllowContentAccess(false);settings.setJavaScriptCanOpenWindowsAutomatically(false);settings.setSupportMultipleWindows(false);settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);settings.setUserAgentString(settings.getUserAgentString()+" SpendSenseAndroid/1.0");
        WebView.setWebContentsDebuggingEnabled(false);CookieManager.getInstance().setAcceptCookie(true);CookieManager.getInstance().setAcceptThirdPartyCookies(web,false);
        web.setWebViewClient(new WebViewClient(){
            @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest request){
                String url=request.getUrl().toString();
                if(url.equals("spendsense://export") && request.isForMainFrame() && ServerAddress.sameOrigin(server,view.getUrl())){exportFinance();return true;}
                if(ServerAddress.sameOrigin(server,url))return false;
                if(request.isForMainFrame() && "https".equals(request.getUrl().getScheme())){startActivity(new Intent(Intent.ACTION_VIEW,request.getUrl()));}
                return true;
            }
            @Override public WebResourceResponse shouldInterceptRequest(WebView view,WebResourceRequest request){
                Uri uri=request.getUrl();String scheme=uri.getScheme();
                if("http".equals(scheme) && !ServerAddress.sameOrigin(server,uri.toString()))return new WebResourceResponse("text/plain","UTF-8",403,"Blocked",java.util.Collections.emptyMap(),new ByteArrayInputStream(new byte[0]));
                return null;
            }
            @Override public void onReceivedSslError(WebView view,SslErrorHandler handler,SslError error){handler.cancel();connectionError("This HTTPS certificate could not be verified. Use a server with a valid certificate; SpendSense never bypasses certificate checks.");}
            @Override public void onReceivedError(WebView view,WebResourceRequest request,WebResourceError error){if(request.isForMainFrame())connectionError("Check your server address, Wi-Fi and that SpendSense is running on your laptop.");}
            @Override public void onReceivedHttpError(WebView view,WebResourceRequest request,WebResourceResponse response){if(request.isForMainFrame())connectionError("The server returned HTTP "+response.getStatusCode()+". Check your SpendSense server.");}
            @Override public void onPageStarted(WebView view,String url,android.graphics.Bitmap icon){progress.setVisibility(View.VISIBLE);}
            @Override public void onPageFinished(WebView view,String url){CookieManager.getInstance().flush();progress.setVisibility(View.GONE);}
        });
        web.setWebChromeClient(new WebChromeClient(){
            @Override public void onProgressChanged(WebView view,int value){progress.setProgress(value);}
            @Override public boolean onShowFileChooser(WebView view,ValueCallback<Uri[]> callback,FileChooserParams params){
                if(upload!=null)upload.onReceiveValue(null);upload=callback;
                Intent pick=new Intent(Intent.ACTION_OPEN_DOCUMENT);pick.addCategory(Intent.CATEGORY_OPENABLE);pick.setType("image/*");pick.putExtra(Intent.EXTRA_MIME_TYPES,new String[]{"image/jpeg","image/png","image/webp"});
                try{startActivityForResult(pick,101);}catch(Exception e){upload.onReceiveValue(null);upload=null;Toast.makeText(MainActivity.this,"No image picker is available.",Toast.LENGTH_LONG).show();}return true;
            }
        });
        web.loadUrl(server);
    }
    private void connectionError(String reason){
        if(failed || content==null)return;failed=true;
        runOnUiThread(()->{LinearLayout panel=new LinearLayout(this);panel.setOrientation(LinearLayout.VERTICAL);panel.setPadding(dp(26),dp(45),dp(26),dp(26));panel.setBackgroundColor(BACKGROUND);panel.addView(text("Your wallet is waiting.",28,TEXT));panel.addView(text(reason,16,MUTED));panel.addView(text(server,14,MINT));Button retry=button("Try again");panel.addView(retry);retry.setOnClickListener(v->openWallet());Button change=button("Change server address");LinearLayout.LayoutParams space=new LinearLayout.LayoutParams(-1,-2);space.topMargin=dp(15);panel.addView(change,space);change.setOnClickListener(v->showSetup());content.addView(panel,new FrameLayout.LayoutParams(-1,-1));progress.setVisibility(View.GONE);});
    }
    private void exportFinance(){
        Toast.makeText(this,"Preparing your finance export…",Toast.LENGTH_SHORT).show();
        new Thread(()->{HttpURLConnection connection=null;try{
            connection=(HttpURLConnection)new URL(server+"api/export").openConnection();connection.setConnectTimeout(10000);connection.setReadTimeout(20000);connection.setInstanceFollowRedirects(false);String cookies=CookieManager.getInstance().getCookie(server);if(cookies!=null)connection.setRequestProperty("Cookie",cookies);
            if(connection.getResponseCode()!=200)throw new Exception("Sign in before exporting your finances.");
            ByteArrayOutputStream bytes=new ByteArrayOutputStream();try(InputStream in=connection.getInputStream()){byte[] buffer=new byte[8192];int n;while((n=in.read(buffer))!=-1){bytes.write(buffer,0,n);if(bytes.size()>2*1024*1024)throw new Exception("Export is too large.");}}
            exportBytes=bytes.toByteArray();runOnUiThread(()->{Intent save=new Intent(Intent.ACTION_CREATE_DOCUMENT);save.addCategory(Intent.CATEGORY_OPENABLE);save.setType("application/json");save.putExtra(Intent.EXTRA_TITLE,"spendsense-finances.json");startActivityForResult(save,102);});
        }catch(Exception e){runOnUiThread(()->Toast.makeText(this,e.getMessage()==null?"Export could not finish.":e.getMessage(),Toast.LENGTH_LONG).show());}finally{if(connection!=null)connection.disconnect();}}).start();
    }
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);
        if(request==101 && upload!=null){upload.onReceiveValue(result==RESULT_OK && data!=null && data.getData()!=null?new Uri[]{data.getData()}:null);upload=null;}
        if(request==102 && exportBytes!=null){if(result==RESULT_OK && data!=null && data.getData()!=null){try(OutputStream out=getContentResolver().openOutputStream(data.getData())){if(out!=null)out.write(exportBytes);Toast.makeText(this,"Finance export saved.",Toast.LENGTH_SHORT).show();}catch(Exception e){Toast.makeText(this,"Could not save the export.",Toast.LENGTH_LONG).show();}}exportBytes=null;}
    }
    @Override public void onBackPressed(){
        if(web!=null && ServerAddress.sameOrigin(server,web.getUrl())){
            web.evaluateJavascript("(function(){if(typeof state!=='undefined' && state.page!=='home'){navigate('home');return true;}return false;})()",result->{if(!"true".equals(result)){if(web!=null && web.canGoBack())web.goBack();else finish();}});
        }else super.onBackPressed();
    }
    @Override protected void onPause(){super.onPause();CookieManager.getInstance().flush();if(web!=null)web.onPause();}
    @Override protected void onResume(){super.onResume();if(web!=null)web.onResume();}
    @Override protected void onDestroy(){if(upload!=null)upload.onReceiveValue(null);if(web!=null)web.destroy();super.onDestroy();}
}
