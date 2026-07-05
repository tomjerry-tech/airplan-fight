function getCookie (name) {
  var strcookie = document.cookie; // 获取cookie字符串
  var arrcookie = strcookie.split(';'); // 分割
  // 遍历匹配
  for (var i = 0; i < arrcookie.length; i++) {
    var arr = arrcookie[i].replace(/^\s+|\s+$/g, '').split('=');
    if (arr[0] === name) {
      return arr[1];
    }
  }
  return '';
}

function getQueryString (name, target) {
  try {
    var reg = new RegExp('(^|&)' + name + '=([^&]*)(&|$)', 'i');
    if (target == null) {
      target = window;
    }
    var r = target.location.search.substr(1).match(reg);
    if (r !== null) {
      return unescape(r[2]);
    }
  } catch (e) {}
  return null;
}

var whiteList = [261337924,2362303732,2115498776,2364678458,1405564344,667177428,554586257,996265692,1989359836,1285275227,500886888,1723834034,537593226,592942648,1759495307,2451820247,2420881482,2388255195,2382578078,2382578665,2382579166,2382579515,2382579892,2575935819,2509422481,2509423538,732341717,2732342259,2732346948,2003484637,2118384058,989535678,2732341717,1889032464,2551018448,2736219851,2736221491,279499036,504235680,1556240342,2875813813,2111611889,3172527170,3175632840,874338946,3181914896,3185952062,3185948017,3270644041,2938641932,3304356129,2397344501,3152862892,3152936953,3152988118,3153139609,3155495235,3156179172,3156220491,3328755485,3304362916,3184282228,3513596624,3513274250,1353450546,2731859907,3645443007,3754628468,3843426510,162146019,3700454804,244902449,244903494,339752590,2928249942,278281025,278058650,237900421,1342259183,250908343,162322240,281386555,282702599,3002814233,3007232961,3000542179,3000534826,3973366593,3793835161,170552038,168691358,168295850,170969276,364943289,101192467,4024314511,4045675348,4014533101,4014680821,4014681437,4016070942,467411594,1040435839,2269655789,2759679865,1416132402,1447543757,1423664973,252394733,262390907,3324814771];

var previewUserId = getCookie('4399_HTML5_PREVIEW_USERID');
var previewMode = false;
var isPreviewDomain = document.domain.indexOf('h5-preview.4399api.com') > -1;
var isOT = getQueryString('runMode') === 'online-test';
var ua = navigator.userAgent;

if (whiteList.indexOf(parseInt(previewUserId)) !== -1) {
  previewMode = true;
} else if (ua.indexOf('4399GameCenter') !== -1 && ua.indexOf('preview') !== -1) {
  previewMode = true;
} else if (ua.indexOf('Zhuoqu') !== -1 && ua.indexOf('preview') !== -1) {
  previewMode = true;
} else if (ua.indexOf('4399wan') !== -1 && ua.indexOf('preview') !== -1) {
  previewMode = true;
} else if (ua.indexOf('shanyi') !== -1 && ua.indexOf('preview') !== -1) {
  previewMode = true;
} else if (isPreviewDomain && isOT) {
  previewMode = true;
}

if (previewMode) { // 预览模式
  document.write('<script type="text/javascript" src="https://cdn.h5wan.4399sj.com/h5mini-2.0/dist_preview/static/js/manifest.a1dc820809717e111875.js"></script><script type="text/javascript" src="https://cdn.h5wan.4399sj.com/h5mini-2.0/dist_preview/static/js/vendor.155ef9fff69c18c4e186.js"></script><script type="text/javascript" src="https://cdn.h5wan.4399sj.com/h5mini-2.0/dist_preview/static/js/app.8e2196b71e18b0e3fc46.js"></script>');
} else {
  document.write('<script type="text/javascript" src="https://cdn.h5wan.4399sj.com/h5mini-2.0/dist/static/js/manifest.d1d177e77983668fe92a.js"></script><script type="text/javascript" src="https://cdn.h5wan.4399sj.com/h5mini-2.0/dist/static/js/vendor.a9fbd3f3d0d3ba3cdd62.js"></script><script type="text/javascript" src="https://cdn.h5wan.4399sj.com/h5mini-2.0/dist/static/js/app.9260cb4a7ef5877b9d59.js"></script>');
}
