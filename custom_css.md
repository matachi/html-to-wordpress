# Custom WordPress CSS

```css
.old_site table {
  margin: 0 auto;
}
.old_site td {
  vertical-align: top;
}
.old_site img {
  height: inherit;
}
.old_site font {
  line-height: 14px;
}
.old_site p {
  line-height: 14px;
  margin-bottom: 16px;
}
.old_site ol, .old_site ul {
  padding-left: 40px;
  counter-reset: li;
}
.old_site ol > li, .old_site ul > li {
  list-style:none;
  position: relative;
}
.old_site ol > li:before {
  content:counter(li); /* Use the counter as content */
  counter-increment:li; /* Increment the counter by 1 */
}
.old_site ul > li:before {
  content: '•';
}
.old_site ol > li:before, .old_site ul > li:before {
  font-size: 20px;
  left: -30px;
  top: -3px;
  position: absolute;
  width: 20px;
  text-align: right;
}
```