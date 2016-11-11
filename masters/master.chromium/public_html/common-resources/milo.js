// Copyright (c) 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

function MiloInject(root, mastername) {
  // Get our ".header" <div> (in "layout.html").
  var header = document.querySelector(".header");
  if (! header) {
    return;
  }

  // Do we have a Milo substitution available?
  var path = window.location.pathname;
  var desc = null;
  var miloPath = path;
  [
    {
      re: /^(?:\/[ip]\/([^\/]+))?\/builders\/([^\/]+)$/,
      desc: "builder faster",
      replacer: function(match, master, builder, offset, string) {
        master = mastername || master;
        if (! master) {
          return string;
        }
        return ["buildbot", master, builder].join("/");
      },
    },
    {
      re: /^(?:\/[ip]\/([^\/]+))?\/builders\/([^\/]+)\/builds\/([^\/]+)$/,
      desc: "build faster and forever",
      replacer: function(match, master, builder, buildno, offset, string) {
        master = mastername || master;
        if (! master) {
          return string;
        }
        return ["buildbot", master, builder, buildno].join("/");
      },
    },
  ].every(function(e) {
    miloPath = path.replace(e.re, e.replacer);
    desc = e.desc;
    return (miloPath === path);
  });
  if (miloPath === path) {
    return;
  }

  // Build our milo elements.
  miloPath = "https://luci-milo.appspot.com/" + miloPath;
  var miloElement = document.createElement("span");
  miloElement.className = "header-right-align";
  miloElement.innerHTML += `
    <div class="milo-container">
      <a class="milo-link" href="${miloPath}">
        <img class=".milo-logo"
            src="${root}common-resources/chrome-infra-logo-32x32.png" /><!--
            -->[LogDog]</a>
      <div class="milo-info">
        <div>View this ${desc} with LogDog / Milo!</div>
        <p></p>
        <div><a href="${miloPath}">Permalink</a></div>
        <p></p>
        <div class="milo-cit-info">
          <img src="${root}common-resources/chrome-infra-logo-32x32.png"></img>
          <span>Part of Chrome Infrastructure Team's LUCI project.</span>
        </div>
      </div>
    </div>
  `;
  header.appendChild(miloElement);
}
